import asyncio

import structlog
from bson import ObjectId

from app.config import get_settings
from app.db.models import AuthConfig, RunConfig, TestCaseInDB
from app.db.repositories import result_repository, run_repository, test_case_repository
from app.executor.engine import TestExecutor

logger = structlog.get_logger()


class RunContext:
    def __init__(self, run_id: ObjectId, config: RunConfig):
        self.run_id = run_id
        self.config = config
        self.in_flight_tasks: dict[str, asyncio.Task] = {}
        self.cancelled = False
        self.cancel_timeout = 10.0

    def add_task(self, test_case_id: str, task: asyncio.Task):
        self.in_flight_tasks[test_case_id] = task

    def remove_task(self, test_case_id: str):
        self.in_flight_tasks.pop(test_case_id, None)

    async def cancel_all(self):
        self.cancelled = True
        if self.in_flight_tasks:
            done, pending = await asyncio.wait(
                self.in_flight_tasks.values(),
                timeout=self.cancel_timeout,
                return_when=asyncio.ALL_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    def is_cancelled(self) -> bool:
        return self.cancelled


class RunOrchestrator:
    def __init__(self):
        self.active_runs: dict[str, RunContext] = {}

    async def execute_run(self, run_id: str, user_id: str):
        run_obj_id = ObjectId(run_id)
        user_obj_id = ObjectId(user_id)

        run = await run_repository.get_by_id(run_obj_id, user_obj_id)
        if not run:
            logger.error("Run not found", run_id=run_id)
            return

        # Fetch spec to get base_url and auth_config for execution context
        from app.db.repositories import spec_repository

        spec = await spec_repository.get_by_id(run.spec_id, user_obj_id)
        if spec:
            # Update run config with spec's base_url and auth_config if not overridden
            if not run.config.base_url_override and spec.base_url:
                run.config.spec_base_url = spec.base_url
            if not run.config.auth_override and spec.auth_config:
                run.config.spec_auth_config = spec.auth_config
            # Persist updated config
            await run_repository.update_config(run_obj_id, run.config)

        # Session credentials are encrypted at rest and never placed in the
        # public run document. Resolve them only in this worker immediately
        # before execution.
        if run.config.auth_secret_ref:
            from app.core.security import decrypt_value
            from app.db.mongo import get_collection

            try:
                session = await get_collection("sessions").find_one(
                    {"_id": ObjectId(run.config.auth_secret_ref), "user_id": user_obj_id}
                )
                if session and session.get("auth_token_encrypted") and session.get("auth_type"):
                    run.config.auth_override = AuthConfig(
                        type=session["auth_type"], token=decrypt_value(session["auth_token_encrypted"])
                    )
                if session and session.get("secondary_auth_token_encrypted") and session.get("secondary_auth_type"):
                    run.config.auth_secondary = AuthConfig(
                        type=session["secondary_auth_type"], token=decrypt_value(session["secondary_auth_token_encrypted"])
                    )
            except Exception as exc:
                logger.error("Unable to resolve encrypted session credentials", error=type(exc).__name__)
                await run_repository.update_status(run_obj_id, "failed")
                return

        await run_repository.update_status(run_obj_id, "running")
        await run_repository.update_started_at(run_obj_id)
        run = await run_repository.get_by_id(run_obj_id, user_obj_id)

        # Server-enforce mode limits (cannot be overridden by client)
        if run.config.mode == "online":
            run.config.concurrency = min(run.config.concurrency, 3)
            if not run.config.rate_limit_rps or run.config.rate_limit_rps > 2.0:
                run.config.rate_limit_rps = 2.0
            if not run.config.owned_host_attestation:
                run.config.categories = [
                    c for c in run.config.categories if c not in ("security", "resource_consumption")
                ]

        context = RunContext(run_obj_id, run.config)
        self.active_runs[run_id] = context

        executor = TestExecutor(
            max_concurrent_requests=run.config.concurrency,
            request_timeout=run.config.timeout_seconds,
            max_retries=run.config.retry_failed,
            rate_limit_rps=run.config.rate_limit_rps,
            max_response_body_bytes=get_settings().max_response_body_bytes,
        )

        try:
            test_cases = await test_case_repository.list_by_spec(
                run.spec_id,
                category=None,
                limit=10000,
            )

            filtered_cases = [tc for tc in test_cases if tc.category in run.config.categories]
            if len(filtered_cases) > run.config.max_total_requests:
                filtered_cases = filtered_cases[: run.config.max_total_requests]
                logger.warning(
                    "Run request budget enforced",
                    run_id=run_id,
                    max_total_requests=run.config.max_total_requests,
                )
            logger.info("Starting test execution", run_id=run_id, total_cases=len(filtered_cases))

            tasks = []
            for tc in filtered_cases:
                if context.is_cancelled():
                    break
                task = asyncio.create_task(self._execute_single(executor, context, tc))
                context.add_task(str(tc.id), task)
                tasks.append(task)

            passed = failed = errors = skipped = blocked = 0

            for task in asyncio.as_completed(tasks):
                if context.is_cancelled():
                    break
                try:
                    result = await task
                    context.remove_task(str(result.test_case_id))

                    # Persist each result immediately
                    await result_repository.create(result)

                    # Update summary counters atomically
                    if result.status == "passed":
                        passed += 1
                        await run_repository.increment_summary(run_obj_id, "passed", 1)
                    elif result.status == "failed":
                        failed += 1
                        await run_repository.increment_summary(run_obj_id, "failed", 1)
                    elif result.status == "error":
                        errors += 1
                        await run_repository.increment_summary(run_obj_id, "errors", 1)
                    elif result.status == "skipped":
                        skipped += 1
                        await run_repository.increment_summary(run_obj_id, "skipped", 1)
                    elif result.status == "blocked":
                        blocked += 1
                        await run_repository.increment_summary(run_obj_id, "blocked", 1)

                except Exception as e:
                    logger.error("Test execution exception", error=str(e))
                    errors += 1
                    await run_repository.increment_summary(run_obj_id, "errors", 1)

            total = passed + failed + errors + skipped + blocked
            await run_repository.increment_summary(run_obj_id, "total", total)

            final_status = (
                "cancelled" if context.is_cancelled() else ("completed_with_errors" if errors > 0 else "completed")
            )
            await run_repository.update_status(run_obj_id, final_status)
            await run_repository.update_completed_at(run_obj_id)

            logger.info(
                "Run completed",
                run_id=run_id,
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                blocked=blocked,
            )

        except Exception as e:
            logger.exception("Run execution failed", run_id=run_id, error=str(e))
            await run_repository.update_status(run_obj_id, "failed")
        finally:
            await executor.close()
            self.active_runs.pop(run_id, None)

    async def _execute_single(self, executor: TestExecutor, context: RunContext, test_case: TestCaseInDB):
        return await executor.execute_test_case(test_case, context)

    async def cancel_run(self, run_id: ObjectId):
        run_id_str = str(run_id)
        context = self.active_runs.get(run_id_str)
        if context:
            await context.cancel_all()
            await run_repository.update_status(run_id, "cancelling")

    async def retry_failed(self, run_id: ObjectId):
        failed_results = await result_repository.list_by_run(run_id, status="failed")
        error_results = await result_repository.list_by_run(run_id, status="error")

        all_failed = failed_results + error_results
        if not all_failed:
            return

        run_doc = await run_repository.collection.find_one({"_id": run_id})
        if not run_doc:
            return

        await run_repository.update_status(run_id, "running")

        test_case_ids = [r.test_case_id for r in all_failed]

        test_cases = []
        for tc_id in test_case_ids:
            tc = await test_case_repository.get_by_id(tc_id)
            if tc:
                test_cases.append(tc)

        run_config = RunConfig(**run_doc.get("config", {}))

        executor = TestExecutor(
            max_concurrent_requests=run_config.concurrency,
            request_timeout=run_config.timeout_seconds,
            max_retries=run_config.retry_failed,
        )

        context = RunContext(run_id, run_config)
        self.active_runs[str(run_id)] = context

        try:
            tasks = []
            for tc in test_cases:
                if context.is_cancelled():
                    break
                task = asyncio.create_task(self._execute_single(executor, context, tc))
                context.add_task(str(tc.id), task)
                tasks.append(task)

            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    existing_res = next(r for r in all_failed if r.test_case_id == result.test_case_id)

                    await result_repository.update_status(existing_res.id, result.status)
                    if result.llm_analysis:
                        await result_repository.update_analysis(existing_res.id, result.llm_analysis.model_dump())
                except Exception as e:
                    logger.error("Retry execution exception", error=str(e))

            await run_repository.update_status(run_id, "completed")

        finally:
            await executor.close()
            self.active_runs.pop(str(run_id), None)
