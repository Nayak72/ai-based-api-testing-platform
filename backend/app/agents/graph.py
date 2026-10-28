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
    try:
        state = await IngestAgent().run(state)
        if state.get("errors"):
            err_msg = "; ".join(state["errors"])
            await get_collection("sessions").update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"status": "failed", "error": err_msg}},
            )
            await publish(
                AgentEvent(
                    session_id=session_id,
                    agent="orchestrator",
                    step="session_error",
                    status="failed",
                    message=f"Pipeline error: {err_msg}",
                )
            )
            return state

        state = await PlannerAgent().run(state)
        if state.get("errors"):
            err_msg = "; ".join(state["errors"])
            await get_collection("sessions").update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"status": "failed", "error": err_msg}},
            )
            await publish(
                AgentEvent(
                    session_id=session_id,
                    agent="orchestrator",
                    step="session_error",
                    status="failed",
                    message=f"Pipeline error: {err_msg}",
                )
            )
            return state

        # Update session with plan and waiting_human=True
        await get_collection("sessions").update_one(
            {"_id": ObjectId(session_id), "status": {"$ne": "cancelled"}},
            {
                "$set": {
                    "status": "waiting_approval",
                    "waiting_human": True,
                    "plan": state.get("plan"),
                }
            },
        )
        return state

    except Exception as e:
        logger.exception("Agentic pipeline failed in ingest/plan phase", error=str(e))
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


async def resume_after_plan_approval(state: SessionState) -> SessionState:
    """
    Resume the pipeline after the user has approved (or edited) the plan.
    Runs: Generate -> Execute -> Triage -> Report.
    """
    from app.agents.reporter import ReporterAgent
    from app.agents.triage import TriageAgent
    from app.api.schemas.runs import RunConfigSchema, RunCreateRequest
    from app.db.mongo import get_collection
    from app.db.repositories import run_repository, test_case_repository
    from app.executor.runner import RunOrchestrator
    from app.generators.orchestrator import GenerationOrchestrator

    session_id = state.get("session_id", "")
    spec_id = state.get("spec_id", "")
    user_id = state.get("user_id", "")
    mode = state.get("mode", "local")

    try:
        # Check if test cases exist, otherwise generate them
        existing_tc_count = await test_case_repository.count_by_spec(ObjectId(spec_id))
        categories = state.get("categories") or ["functional", "edge", "malformed", "security"]

        if existing_tc_count == 0:
            await publish(
                AgentEvent(
                    session_id=session_id,
                    agent="generator",
                    step="generate",
                    status="started",
                    message=f"Generating test cases for {len(categories)} categories...",
                )
            )
            gen = GenerationOrchestrator()

            async def report_generation(category: str, status: str, message: str) -> None:
                await publish(
                    AgentEvent(
                        session_id=session_id,
                        agent="generator",
                        step="generate",
                        status=status,
                        message=message,
                    )
                )

            await gen.generate_for_spec(
                spec_id=spec_id,
                user_id=user_id,
                categories=categories,
                progress_callback=report_generation,
            )
            tc_count = await test_case_repository.count_by_spec(ObjectId(spec_id))
            if tc_count == 0:
                raise RuntimeError("Test generation produced no test cases")
            await publish(
                AgentEvent(
                    session_id=session_id,
                    agent="generator",
                    step="generate",
                    status="completed",
                    message=f"Generated {tc_count} test cases",
                )
            )

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
        await publish(
            AgentEvent(
                session_id=session_id,
                agent="executor",
                step="execute",
                status=final_status,
                message="Test execution finished",
            )
        )

        # Triage and Report
        state = await TriageAgent().run(state)
        state = await ReporterAgent().run(state)

        # Mark session completed
        final_status = "completed_with_errors" if run.status == "completed_with_errors" else "completed"
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
