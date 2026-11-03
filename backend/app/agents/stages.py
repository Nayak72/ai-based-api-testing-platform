"""Durable stage transitions for resumable agent sessions."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from app.agents.events import AgentEvent, publish
from app.db.mongo import get_collection

STAGE_IDS = ("ingest", "plan", "generate", "execute", "triage", "report")
StageStatus = Literal[
    "pending", "running", "waiting", "completed", "completed_with_errors", "failed", "skipped", "cancelled"
]


def initial_stages() -> dict[str, dict[str, Any]]:
    return {
        stage: {
            "status": "pending",
            "started_at": None,
            "finished_at": None,
            "progress": {"done": 0, "total": 0, "failed": 0},
            "error": None,
        }
        for stage in STAGE_IDS
    }


class StageTracker:
    def __init__(self, session_id: str, *, heartbeat_interval: float = 5.0) -> None:
        self.session_id = session_id
        self._id = ObjectId(session_id)
        self._heartbeat_interval = heartbeat_interval
        self._last_progress_write: dict[str, float] = {}
        self._heartbeat_task: asyncio.Task | None = None
        self._closed = False

    @property
    def collection(self):
        return get_collection("sessions")

    async def _write_and_publish(self, update: dict, *, stage: str, message: str) -> None:
        await self.collection.update_one({"_id": self._id}, update)
        session = await self.collection.find_one({"_id": self._id}, {"stages": 1})
        await publish(
            AgentEvent(
                session_id=self.session_id,
                agent="pipeline",
                step=stage,
                status="progress",
                message=message,
                type="stage_update",
                data={"stages": (session or {}).get("stages", {})},
            )
        )

    def _ensure_heartbeat(self) -> None:
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        while not self._closed:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self.collection.update_one(
                    {"_id": self._id, "status": "running"},
                    {"$set": {"heartbeat_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}},
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                # The owning stage will surface persistent database failures.
                continue

    async def start(self, stage: str, total: int | None = None) -> None:
        progress = {"done": 0, "total": total or 0, "failed": 0}
        now = datetime.now(UTC)
        # close() runs whenever no stage is active; reopen so the heartbeat loop
        # keeps running for the next stage instead of exiting immediately.
        self._closed = False
        await self._write_and_publish(
            {
                "$set": {
                    "status": "running",
                    "current_stage": stage,
                    "heartbeat_at": now,
                    "updated_at": now,
                    f"stages.{stage}.status": "running",
                    f"stages.{stage}.started_at": now,
                    f"stages.{stage}.finished_at": None,
                    f"stages.{stage}.progress": progress,
                    f"stages.{stage}.error": None,
                }
            },
            stage=stage,
            message=f"{stage} stage started",
        )
        self._ensure_heartbeat()

    async def progress(self, stage: str, done: int, failed: int, total: int) -> None:
        loop_time = asyncio.get_running_loop().time()
        if loop_time - self._last_progress_write.get(stage, 0) < 1.0 and done < total:
            return
        self._last_progress_write[stage] = loop_time
        now = datetime.now(UTC)
        await self._write_and_publish(
            {
                "$set": {
                    f"stages.{stage}.progress": {"done": done, "total": total, "failed": failed},
                    "heartbeat_at": now,
                    "updated_at": now,
                }
            },
            stage=stage,
            message=f"{stage}: {done}/{total} complete, {failed} failed",
        )

    async def finish(self, stage: str, status: StageStatus, error: str | None = None) -> None:
        now = datetime.now(UTC)
        fields = {
            f"stages.{stage}.status": status,
            f"stages.{stage}.finished_at": now,
            f"stages.{stage}.error": error,
            "heartbeat_at": now,
            "updated_at": now,
        }
        if stage == "plan" and status == "completed":
            fields.update({"status": "running", "waiting_human": False, "waiting_reason": None})
        await self._write_and_publish(
            {"$set": fields},
            stage=stage,
            message=f"{stage} stage {status}" + (f": {error}" if error else ""),
        )
        session = await self.collection.find_one({"_id": self._id}, {"stages": 1})
        active = any((session or {}).get("stages", {}).get(s, {}).get("status") == "running" for s in STAGE_IDS)
        if not active:
            await self.close()

    async def wait(self, stage: str, details: dict | None = None) -> int | None:
        now = datetime.now(UTC)
        update: dict[str, Any] = {
            "$set": {
                "status": "waiting_approval" if stage == "plan" else "waiting_approval",
                "waiting_human": True,
                "current_stage": stage,
                "heartbeat_at": now,
                "updated_at": now,
                f"stages.{stage}.status": "waiting",
                f"stages.{stage}.finished_at": now,
            }
        }
        if details:
            update["$set"].update(details)
        if stage == "plan":
            update["$inc"] = {"plan_version": 1}
        result = await self.collection.update_one({"_id": self._id}, update)
        session = await self.collection.find_one({"_id": self._id}, {"stages": 1, "plan_version": 1})
        await publish(
            AgentEvent(
                session_id=self.session_id,
                agent="pipeline",
                step=stage,
                status="waiting_human",
                message=f"{stage} stage is waiting for approval",
                type="stage_update",
                data={"stages": (session or {}).get("stages", {}), "plan_version": (session or {}).get("plan_version", 0)},
            )
        )
        await self.close()
        return (session or {}).get("plan_version") if result.modified_count else None

    async def close(self) -> None:
        self._closed = True
        if self._heartbeat_task and self._heartbeat_task is not asyncio.current_task():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None


class CancelToken:
    """Poll persisted cancellation state and wake active workers promptly."""

    def __init__(self, session_id: str, poll_seconds: float = 1.0) -> None:
        self.session_id = session_id
        self._id = ObjectId(session_id)
        self.poll_seconds = poll_seconds

    async def cancelled(self) -> bool:
        doc = await get_collection("sessions").find_one({"_id": self._id}, {"status": 1})
        return not doc or doc.get("status") == "cancelled"

    async def wait(self) -> None:
        while not await self.cancelled():
            await asyncio.sleep(self.poll_seconds)


async def emit_terminal(session_id: str, outcome: str, message: str, *, error: str | None = None) -> bool:
    """Persist one terminal outcome and publish it only if no terminal was emitted."""
    collection = get_collection("sessions")
    status = {"session_done": "completed", "session_error": "failed", "session_cancelled": "cancelled"}[outcome]
    now = datetime.now(UTC)
    result = await collection.update_one(
        {"_id": ObjectId(session_id), "terminal_event": {"$exists": False}},
        {"$set": {"status": status, "terminal_event": outcome, "error": error, "updated_at": now}},
    )
    if result.modified_count:
        await publish(
            AgentEvent(
                session_id=session_id,
                agent="orchestrator",
                step=outcome,
                status="failed" if outcome == "session_error" else "completed",
                message=message,
                type="log",
            )
        )
        return True
    return False
