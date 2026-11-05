from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import structlog
from bson import ObjectId

from app.ai import create_orchestrator
from app.config import get_settings
from app.db.mongo import get_collection
from app.db.repositories import generation_unit_repository
from app.generators.functional import EdgeGenerator, FunctionalGenerator, MalformedGenerator, SecurityGenerator
from app.generators.deterministic import DeterministicGenerator
from app.parsers import extract_endpoints

logger = structlog.get_logger()


class GenerationOrchestrator:
    def __init__(self, primary_provider: str | None = None, model: str | None = None, api_key: str | None = None):
        self.model = model
        self.settings = get_settings()
        self.ai_orchestrator = create_orchestrator(primary_provider=primary_provider, model=model, api_key=api_key)
        self.generators = {
            "functional": FunctionalGenerator(self.ai_orchestrator),
            "edge": EdgeGenerator(self.ai_orchestrator),
            "malformed": MalformedGenerator(self.ai_orchestrator),
            "security": SecurityGenerator(self.ai_orchestrator),
        }
        self.deterministic = DeterministicGenerator()

    async def generate_for_spec(
        self,
        spec_id: str,
        user_id: str,
        categories: list[str],
        prompt_version: str = "v2",
        dry_run: bool = False,
        model: str | None = None,
        progress_callback: Callable[..., Awaitable[None]] | None = None,
        plan: dict | None = None,
        session_id: str | None = None,
        only_failed: bool = False,
        cancel_token=None,
    ) -> dict:
        from app.db.repositories import spec_repository, test_case_repository

        spec_obj_id = ObjectId(spec_id)
        spec = await spec_repository.get_by_id(spec_obj_id, ObjectId(user_id))
        if not spec or not spec.parsed_spec:
            raise ValueError("Spec not found or not parsed")
        endpoints = extract_endpoints(spec.parsed_spec)
        endpoint_by_id = {ep["endpoint_id"]: ep for ep in endpoints}
        plan_units = (plan or {}).get("endpoints", [])
        if plan is not None:
            requested = [(item["endpoint_id"], category) for item in plan_units for category in item.get("categories", [])]
        else:
            requested = [(endpoint["endpoint_id"], category) for endpoint in endpoints for category in categories]
        requested = [(ep_id, category) for ep_id, category in requested if ep_id in endpoint_by_id and category in self.generators]

        units = []
        for endpoint_id, category in requested:
            generator = self.generators[category]
            endpoint = endpoint_by_id[endpoint_id]
            plan_item = next((item for item in plan_units if item.get("endpoint_id") == endpoint_id), {})
            planned_subcats = plan_item.get("subcategories") or []
            subcategories = planned_subcats or (generator.SUBCATEGORIES if (session_id and self._intensity(session_id) == "aggressive") else ["all"])
            for subcategory in subcategories:
                deterministic_cases = self.deterministic.generate(
                    spec_id=spec_obj_id,
                    endpoint=endpoint,
                    category=category,
                    subcategory=subcategory,
                )
                unit = None
                if session_id:
                    unit = await generation_unit_repository.ensure(
                        session_id=session_id,
                        spec_id=spec_obj_id,
                        endpoint_id=endpoint_id,
                        category=category,
                        subcategory=subcategory,
                    )
                units.append((endpoint_by_id[endpoint_id], category, subcategory, unit))

        total = len(units)
        if not total:
            raise ValueError("Approved plan contains no supported generation units")
        done = failed = tokens = 0
        errors: list[str] = []
        semaphore = asyncio.Semaphore(max(1, min(self.settings.generation_concurrency, self.settings.online_max_concurrency if self._mode(session_id) == "online" else self.settings.generation_concurrency)))
        progress_lock = asyncio.Lock()

        async def report(category: str, status: str, message: str, metrics: dict | None = None) -> None:
            if progress_callback:
                await progress_callback(category, status, message, metrics or {})

        async def generate_one(endpoint: dict, category: str, subcategory: str, unit: dict | None) -> None:
            nonlocal done, failed, tokens
            unit_id = str(unit["_id"]) if unit else None
            if unit and unit.get("status") == "done" and not only_failed:
                async with progress_lock:
                    done += 1
                    await report(category, "progress", f"Skipped completed unit {endpoint['endpoint_id']} · {category}", {"done": done, "failed": failed, "total": total})
                return
            if only_failed and unit and unit.get("status") not in {"failed", "pending"}:
                async with progress_lock:
                    done += 1
                    await report(category, "progress", f"Skipped unit {endpoint['endpoint_id']} · {category}", {"done": done, "failed": failed, "total": total})
                return
            if cancel_token and await cancel_token.cancelled():
                if unit:
                    await generation_unit_repository.finish(ObjectId(unit_id), status="cancelled", error="Session cancelled")
                raise asyncio.CancelledError

            generator = self.generators[category]
            started = datetime.now(UTC)
            if unit:
                await generation_unit_repository.start(ObjectId(unit_id))
            await report(category, "progress", f"Generating {category}/{subcategory}: {endpoint['endpoint_id']}", {"done": done, "failed": failed, "total": total})
            async with semaphore:
                call_task = asyncio.create_task(
                    generator.generate_for_endpoint(
                        spec_id=spec_obj_id,
                        endpoint=endpoint,
                        spec=spec.parsed_spec,
                        subcategory=subcategory,
                        model=model or self.model,
                        prompt_version=prompt_version,
                    )
                )
                cancel_task = asyncio.create_task(cancel_token.wait()) if cancel_token else None
                try:
                    async with asyncio.timeout(self.settings.unit_deadline_seconds):
                        wait_set = {call_task}
                        if cancel_task:
                            wait_set.add(cancel_task)
                        finished, _ = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED)
                        if cancel_task and cancel_task in finished:
                            call_task.cancel()
                            await asyncio.gather(call_task, return_exceptions=True)
                            if unit:
                                await generation_unit_repository.finish(ObjectId(unit_id), status="cancelled", error="Session cancelled")
                            raise asyncio.CancelledError
                        test_cases = deterministic_cases + await call_task
                    if subcategory != "all":
                        for testcase in test_cases:
                            testcase.subcategory = subcategory
                    # Keep contract-derived cases even if an LLM returns too many additions.
                    test_cases = test_cases[: self.settings.max_tests_per_call]
                    for testcase in test_cases:
                        testcase.session_id = session_id
                        testcase.unit_id = unit_id
                    if not dry_run and test_cases:
                        await test_case_repository.bulk_upsert(test_cases)
                    persisted_cases = await test_case_repository.list_by_session(
                        session_id, endpoint_id=endpoint["endpoint_id"], category=category
                    ) if session_id else []
                    response_tokens = test_cases[0].metadata.tokens_used if test_cases else 0
                    tokens += response_tokens
                    if unit:
                        await generation_unit_repository.finish(
                            ObjectId(unit_id), status="done", tokens=response_tokens,
                            test_case_ids=[str(tc.id) for tc in persisted_cases if tc.unit_id == unit_id],
                        )
                    elapsed = int((datetime.now(UTC) - started).total_seconds() * 1000)
                    provider_name = test_cases[0].metadata.generated_by if test_cases else None
                    await report(category, "progress", f"Generated {len(test_cases)} tests: {endpoint['endpoint_id']} · {category}/{subcategory}", {"provider": provider_name, "model": model or self.model, "tokens": response_tokens, "latency_ms": elapsed})
                    async with progress_lock:
                        done += 1
                        await report(category, "progress", f"Generation progress {done}/{total}", {"done": done, "failed": failed, "total": total})
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    if not call_task.done():
                        call_task.cancel()
                        await asyncio.gather(call_task, return_exceptions=True)
                    # Contract-derived cases remain useful and safe when the
                    # optional AI enhancement is unavailable or malformed.
                    if deterministic_cases and isinstance(exc, (ProviderError, ValueError)):
                        for testcase in deterministic_cases:
                            testcase.session_id = session_id
                            testcase.unit_id = unit_id
                        if not dry_run:
                            await test_case_repository.bulk_upsert(deterministic_cases)
                        persisted_cases = await test_case_repository.list_by_session(
                            session_id, endpoint_id=endpoint["endpoint_id"], category=category
                        ) if session_id else []
                        if unit:
                            await generation_unit_repository.finish(
                                ObjectId(unit_id), status="done", tokens=0,
                                test_case_ids=[str(tc.id) for tc in persisted_cases if tc.unit_id == unit_id],
                            )
                        async with progress_lock:
                            done += 1
                        await report(category, "progress", f"Saved {len(deterministic_cases)} contract-derived tests after AI fallback: {endpoint['endpoint_id']}", {"done": done, "failed": failed, "total": total, "fallback": "deterministic"})
                        logger.warning("AI generation fell back to contract-derived cases", endpoint_id=endpoint["endpoint_id"], category=category, error_type=type(exc).__name__)
                        return
                    failed += 1
                    error_code = getattr(exc, "code", "unit_error")
                    error = str(exc)
                    errors.append(f"{category}/{subcategory} {endpoint['endpoint_id']}: {error}")
                    if unit:
                        await generation_unit_repository.finish(ObjectId(unit_id), status="failed", error_code=error_code, error=error)
                    async with progress_lock:
                        done += 1
                    await report(category, "progress", f"Unit failed: {endpoint['endpoint_id']} · {error}", {
                        "done": done, "failed": failed, "total": total,
                        "provider": getattr(getattr(exc, "provider", None), "value", None),
                        "model": model or self.model,
                        "error_code": error_code,
                    })
                    logger.warning("Generation unit failed", unit_id=unit_id, endpoint_id=endpoint["endpoint_id"], category=category, error=error)
                finally:
                    if not call_task.done():
                        call_task.cancel()
                        await asyncio.gather(call_task, return_exceptions=True)
                    if cancel_task:
                        cancel_task.cancel()
                        await asyncio.gather(cancel_task, return_exceptions=True)

        results = await asyncio.gather(*(generate_one(*unit) for unit in units), return_exceptions=True)
        if any(isinstance(result, asyncio.CancelledError) for result in results):
            raise asyncio.CancelledError

        # Coverage measures completed units against all approved units.
        coverage = (total - failed) / total
        return {
            "total": total,
            "done": total - failed,
            "failed": failed,
            "tokens": tokens,
            "coverage": coverage,
            "errors": errors,
            "root_cause": errors[0] if errors else None,
        }

    def _session_value(self, session_id: str | None, key: str, fallback):
        if not session_id:
            return fallback
        # Values are set on the orchestrator by the session worker, without exposing
        # credentials or adding a second database query per unit.
        return getattr(self, f"_session_{key}", fallback)

    def _intensity(self, session_id: str | None) -> str:
        return self._session_value(session_id, "intensity", "standard")

    def _mode(self, session_id: str | None) -> str:
        return self._session_value(session_id, "mode", "local")

    async def close(self) -> None:
        await self.ai_orchestrator.close()
