"""Mongo-backed entry point for starting and resuming session pipelines."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from bson import ObjectId

from app.db.mongo import get_collection

logger = structlog.get_logger()
_active_sessions: set[str] = set()


class PipelineRunner:
    @classmethod
    async def run(cls, session_id: str, from_stage: str | None = None, **overrides) -> None:
        if session_id in _active_sessions:
            logger.info("Session worker already active", session_id=session_id)
            return
        _active_sessions.add(session_id)
        try:
            doc = await get_collection("sessions").find_one({"_id": ObjectId(session_id)})
            if not doc or doc.get("status") in {"completed", "completed_with_errors", "failed", "cancelled"}:
                return
            state = {
                "session_id": session_id,
                "spec_id": str(doc["spec_id"]),
                "user_id": str(doc["user_id"]),
                "mode": getattr(doc.get("mode", "local"), "value", doc.get("mode", "local")),
                "base_url": doc.get("base_url", ""),
                "categories": doc.get("categories", ["functional", "edge", "malformed", "security"]),
                "intensity": doc.get("intensity", "standard"),
                "owned_host_attestation": doc.get("owned_host_attestation", False),
                "routing": {"provider_profile_id": str(doc["provider_profile_id"])} if doc.get("provider_profile_id") else {},
                "plan": doc.get("plan"),
                "run_id": str(doc["run_id"]) if doc.get("run_id") else None,
                "test_cases": [],
                "results": [],
                "errors": [],
                "interrupts": [],
                "human_input": {"plan_approved": bool(doc.get("plan_approved"))},
            }
            if from_stage:
                state["resume_from_stage"] = from_stage
            elif doc.get("current_stage") and doc.get("current_stage") != "ingest":
                state["resume_from_stage"] = doc["current_stage"]
            state.update(overrides)

            if doc.get("status") == "waiting_approval":
                return
            if not doc.get("plan_approved") and state.get("resume_from_stage") in {"plan", "generate", "execute", "triage", "report"}:
                state.pop("resume_from_stage", None)
            if state.get("resume_from_stage"):
                from app.agents.graph import resume_after_plan_approval

                await resume_after_plan_approval(state)
            else:
                from app.agents.graph import run_agentic_pipeline

                await run_agentic_pipeline(state)
        except Exception:
            logger.exception("Pipeline worker crashed", session_id=session_id)
            await get_collection("sessions").update_one(
                {"_id": ObjectId(session_id), "status": {"$ne": "cancelled"}},
                {"$set": {"status": "failed", "error": "Pipeline worker crashed", "updated_at": datetime.now(UTC)}},
            )
        finally:
            _active_sessions.discard(session_id)


async def recover_stale_sessions() -> int:
    """Schedule stale workers after a reload, using persisted stage/unit progress."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.resume_sessions_on_startup:
        return 0
    cutoff = datetime.now(UTC) - timedelta(seconds=60)
    cursor = get_collection("sessions").find(
        {"status": "running", "$or": [{"heartbeat_at": {"$lt": cutoff}}, {"heartbeat_at": {"$exists": False}}]},
        {"_id": 1, "current_stage": 1},
    )
    stale = await cursor.to_list(length=1000)
    for session in stale:
        session_id = str(session["_id"])
        stage = session.get("current_stage")
        if stage == "generate":
            await get_collection("generation_units").update_many(
                {"session_id": session_id, "status": "running"},
                {"$set": {"status": "pending", "error_code": None, "error": None}},
            )
        asyncio.create_task(PipelineRunner.run(session_id, from_stage=stage))
    return len(stale)
