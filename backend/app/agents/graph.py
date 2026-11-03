"""
Agentic pipeline orchestrator.

Ingest → Plan → [interrupt: approve_plan] → (generate + execute) → Triage → Report

When AGENTIC_MODE=false (default), this module is still importable but the legacy
pipeline path is used, enabling A/B comparison via the AGENTIC_MODE feature flag.
"""

from __future__ import annotations

import structlog
from bson import ObjectId

from app.agents.events import AgentEvent, publish
from app.agents.state import SessionState
from app.agents.stages import CancelToken, StageTracker, emit_terminal
from app.generators.policy import coverage_decision

logger = structlog.get_logger()


async def run_agentic_pipeline(state: SessionState) -> SessionState:
    """
    Start the agentic pipeline.
    Phase 1: Ingest + Plan. After plan approval the session resumes via resume_after_plan_approval().
    """
    from app.agents.ingest import IngestAgent
    from app.agents.planner import PlannerAgent
    from app.db.mongo import get_collection

    session_id = state.get("session_id", "")
    tracker = StageTracker(session_id)
    try:
        await tracker.start("ingest")
        state = await IngestAgent().run(state)
        if state.get("errors"):
            err_msg = "; ".join(state["errors"])
            await tracker.finish("ingest", "failed", err_msg)
            await emit_terminal(session_id, "session_error", f"Pipeline error: {err_msg}", error=err_msg)
            return state

        await tracker.finish("ingest", "completed")
        await tracker.start("plan")
        state = await PlannerAgent().run(state)
        if state.get("errors"):
            err_msg = "; ".join(state["errors"])
            await tracker.finish("plan", "failed", err_msg)
            await emit_terminal(session_id, "session_error", f"Pipeline error: {err_msg}", error=err_msg)
            return state

        # Validate both configured routes before creating an approval gate. A plan
        # should not authorize a run whose primary and fallback models are invalid.
        from app.ai import create_orchestrator
        from app.ai.providers.base import GenerationRequest
        ai = create_orchestrator()
        provider_health = {}
        try:
            for provider in ai.providers:
                model_check = await provider.validate_model()
                canary = None
                if model_check.get("ok"):
                    try:
                        response = await provider.generate(
                            GenerationRequest(
                                prompt="Reply with OK.",
                                max_tokens=16,
                                response_format="text",
                                allow_truncated=True,
                            )
                        )
                        # Reaching here means HTTP 200 with a well-formed completion; with a tiny
                        # token budget (or reasoning models) the output may legitimately be cut off.
                        canary = {"ok": True, "latency_ms": response.latency_ms, "finish_reason": response.finish_reason}
                    except Exception as exc:
                        canary = {"ok": False, "error": str(exc)}
                provider_health[provider.name.value] = {
                    **model_check,
                    "canary": canary,
                    "ok": bool(model_check.get("ok") and canary and canary.get("ok")),
                }
        finally:
            await ai.close()
        state["provider_health"] = provider_health
        if not all(item.get("ok") for item in provider_health.values()):
            failures = [
                f"{name}: {item.get('error') or (item.get('canary') or {}).get('error') or 'unhealthy'}"
                for name, item in provider_health.items()
                if not item.get("ok")
            ]
            await get_collection("sessions").update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"provider_health": provider_health, "status": "failed", "error": "; ".join(failures)}},
            )
            await publish(
                AgentEvent(
                    session_id=session_id,
                    agent="orchestrator",
                    step="session_error",
                    status="failed",
                    message="Provider preflight failed: " + "; ".join(failures),
                    data={"provider_health": provider_health},
                )
            )
            return state

        # Update session with plan and waiting_human=True
        await tracker.wait(
            "plan",
            {
                "plan": state.get("plan"),
                "provider_health": provider_health,
                "waiting_reason": "plan_approval",
            },
        )
        return state

    except Exception as e:
        logger.exception("Agentic pipeline failed in ingest/plan phase", error=type(e).__name__)
        state.setdefault("errors", []).append(str(e))
        session = await get_collection("sessions").find_one({"_id": ObjectId(session_id)}, {"current_stage": 1})
        stage = (session or {}).get("current_stage", "ingest")
        await tracker.finish(stage, "failed", str(e))
        await emit_terminal(session_id, "session_error", f"Pipeline error: {e}", error=str(e))
        return state


async def resume_after_plan_approval(state: SessionState) -> SessionState:
    """
    Resume the pipeline after the user has approved (or edited) the plan.
    Runs: Generate -> Execute -> Triage -> Report.
    """
    from app.agents.reporter import ReporterAgent
    from app.agents.triage import TriageAgent
    from app.api.schemas.runs import RunConfigSchema, RunCreateRequest
    from app.db.mongo import get_collection
    from app.db.repositories import provider_repository, run_repository, test_case_repository
    from app.executor.runner import RunOrchestrator
    from app.generators.orchestrator import GenerationOrchestrator

    session_id = state.get("session_id", "")
    spec_id = state.get("spec_id", "")
    user_id = state.get("user_id", "")
    mode = state.get("mode", "local")

    try:
        # Generation is idempotent through the generation cache/upsert layer. Always
        # invoke it for the requested units so a partially completed prior run can
        # fill missing endpoint/category coverage.
        categories = state.get("categories") or ["functional", "edge", "malformed", "security"]

        await publish(
                AgentEvent(
                    session_id=session_id,
                    agent="generator",
                    step="generate",
                    status="started",
                    message=f"Generating test cases for {len(categories)} categories...",
                )
        )
        primary_provider = None
        selected_model = None
        selected_api_key = None
        profile_id = (state.get("routing") or {}).get("provider_profile_id")
        if profile_id:
            profile = await provider_repository.get_by_id(ObjectId(profile_id), ObjectId(user_id))
            if profile:
                primary_provider = profile.preset.value
                selected_model = profile.model
                selected_api_key = provider_repository.get_decrypted_key(profile)
        gen = GenerationOrchestrator(
            primary_provider=primary_provider,
            model=selected_model,
            api_key=selected_api_key,
        )
        gen._session_mode = mode
        gen._session_intensity = state.get("intensity", "standard")
        tracker = StageTracker(session_id)
        await tracker.start("generate")

        async def report_generation(category: str, status: str, message: str, metrics: dict | None = None) -> None:
            metrics = metrics or {}
            if "done" in metrics:
                await tracker.progress("generate", metrics["done"], metrics.get("failed", 0), metrics.get("total", 0))
            if message.startswith(("Generated", "Unit failed")):
                await publish(
                    AgentEvent(
                        session_id=session_id,
                        agent="generator",
                        step="generate",
                        status="failed" if message.startswith("Unit failed") else "progress",
                        message=message,
                        tokens=metrics.get("tokens", 0),
                        latency_ms=metrics.get("latency_ms", 0),
                        provider=metrics.get("provider"),
                        model=metrics.get("model"),
                    )
                )

        if state.get("continue_partial"):
            from app.db.repositories import generation_unit_repository

            prior_units = await generation_unit_repository.list_for_session(session_id)
            generation_result = {
                "total": len(prior_units),
                "done": sum(unit.get("status") in {"done", "skipped"} for unit in prior_units),
                "failed": sum(unit.get("status") == "failed" for unit in prior_units),
                "coverage": sum(unit.get("status") in {"done", "skipped"} for unit in prior_units) / max(1, len(prior_units)),
                "root_cause": None,
            }
        else:
            generation_result = await gen.generate_for_spec(
                spec_id=spec_id,
                user_id=user_id,
                categories=categories,
                progress_callback=report_generation,
                plan=state.get("plan"),
                session_id=session_id,
                only_failed=state.get("retry_failed_units", False),
                cancel_token=CancelToken(session_id),
            )
        await gen.close()
        tc_count = len(await test_case_repository.list_by_session(session_id))
        decision = coverage_decision(
            generation_result["total"], generation_result["done"], generation_result["failed"],
            gen.settings.min_generation_coverage,
        )
        if decision.status == "failed":
            root_cause = generation_result.get("root_cause") or "All planned generation units failed"
            await tracker.finish("generate", "failed", root_cause)
            await emit_terminal(session_id, "session_error", root_cause, error=root_cause)
            return state
        if decision.status == "waiting" and not state.get("continue_partial"):
            await tracker.wait(
                "generate",
                {"waiting_reason": "generation_partial", "waiting_human": True},
            )
            return state
        generation_status = "completed_with_errors" if generation_result["failed"] else "completed"
        await tracker.finish("generate", generation_status)
        await publish(
                AgentEvent(
                    session_id=session_id,
                    agent="generator",
                    step="generate",
                    status=generation_status,
                    message=(
                        f"Generated {tc_count} test cases; {generation_result['failed']} generation units failed"
                        if generation_result.get("failed")
                        else f"Generated {tc_count} test cases"
                    ),
                )
        )

        scoped_cases = await test_case_repository.list_by_session(session_id, limit=10000)
        scoped_cases = [tc for tc in scoped_cases if tc.category in categories]
        test_case_ids = [str(tc.id) for tc in scoped_cases]

        # Create test run if not present
        if not state.get("run_id"):
            run_config = RunConfigSchema(
                categories=categories,
                base_url_override=state.get("base_url") or None,
                mode=mode,
                intensity=state.get("intensity", "standard"),
                owned_host_attestation=state.get("owned_host_attestation", False),
                routing=state.get("routing") or None,
                auth_secret_ref=session_id,
                test_case_ids=test_case_ids,
                session_id=session_id,
            )
            req = RunCreateRequest(
                spec_id=spec_id,
                name=f"Session {session_id[:8]} Run",
                config=run_config,
            )
            run = await run_repository.create(req, ObjectId(user_id))
            state["run_id"] = str(run.id)
            await get_collection("sessions").update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"run_id": str(run.id), "status": "running"}},
            )

        # Execute run
        await publish(
            AgentEvent(
                session_id=session_id,
                agent="executor",
                step="execute",
                status="started",
                message="Executing test suite...",
            )
        )
        orchestrator = RunOrchestrator()
        await orchestrator.execute_run(state["run_id"], user_id)
        run = await run_repository.get_by_id(ObjectId(state["run_id"]), ObjectId(user_id))
        if not run or run.status in ("failed", "cancelled"):
            raise RuntimeError("Test execution did not complete successfully")
        final_status = "completed_with_errors" if run.status == "completed_with_errors" else "completed"
        await publish(
            AgentEvent(
                session_id=session_id,
                agent="executor",
                step="execute",
                status="completed_with_errors" if final_status == "completed_with_errors" else "completed",
                message="Test execution finished",
            )
        )

        # Triage and Report
        state = await TriageAgent().run(state)
        state = await ReporterAgent().run(state)

        # Mark session completed
        session_update = await get_collection("sessions").update_one(
            {"_id": ObjectId(session_id), "status": "running"},
            {"$set": {"status": final_status}},
        )
        if session_update.modified_count != 1:
            raise RuntimeError("Session was cancelled before completion")
        await publish(
            AgentEvent(
                session_id=session_id,
                agent="reporter",
                step="session_done",
                status="completed",
                message="Session completed with errors" if final_status == "completed_with_errors" else "Session completed successfully",
                data={"run_id": state.get("run_id")},
            )
        )
        return state

    except Exception as e:
        logger.exception("Pipeline resume failed", error=str(e))
        state.setdefault("errors", []).append(str(e))
        await get_collection("sessions").update_one(
            {"_id": ObjectId(session_id), "status": {"$ne": "cancelled"}},
            {"$set": {"status": "failed", "error": str(e)}},
        )
        await publish(
            AgentEvent(
                session_id=session_id,
                agent="orchestrator",
                step="session_error",
                status="failed",
                message=f"Pipeline error: {e}",
            )
        )
        return state
