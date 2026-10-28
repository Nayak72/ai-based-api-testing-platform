"""Session routes — agentic pipeline sessions with SSE event streaming."""

from __future__ import annotations

import asyncio
import datetime
import json
from collections.abc import AsyncGenerator

import structlog
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.events import AgentEvent, subscribe, unsubscribe
from app.agents.graph import resume_after_plan_approval, run_agentic_pipeline
from app.agents.state import SessionState
from app.api.deps import CurrentUserId
from app.core.security import encrypt_value
from app.db.mongo import get_collection

logger = structlog.get_logger()
router = APIRouter()


class SessionCreate(BaseModel):
    spec_id: str
    name: str
    mode: str = "local"
    base_url: str | None = None
    auth_type: str | None = None
    auth_token: str | None = None
    provider_profile_id: str | None = None
    categories: list[str] | None = None
    intensity: str = "normal"
    agentic: bool = False


class PlanApproval(BaseModel):
    approved: bool
    modified_plan: list[dict] | None = None


class AuthProvision(BaseModel):
    token: str


@router.post("", status_code=201)
async def create_session(
    body: SessionCreate,
    background_tasks: BackgroundTasks,
    user_id: CurrentUserId,
):
    """Create a new agentic test session."""
    now = datetime.datetime.now(datetime.UTC)
    doc = {
        "spec_id": ObjectId(body.spec_id),
        "user_id": user_id,
        "name": body.name,
        "status": "pending",
        "mode": body.mode,
        "base_url": body.base_url,
        "auth_type": body.auth_type,
        "provider_profile_id": ObjectId(body.provider_profile_id) if body.provider_profile_id else None,
        "categories": body.categories,
        "intensity": body.intensity,
        "agentic": body.agentic,
        "created_at": now,
        "updated_at": now,
    }
    result = await get_collection("sessions").insert_one(doc)
    session_id = str(result.inserted_id)

    state: SessionState = {
        "session_id": session_id,
        "spec_id": body.spec_id,
        "user_id": str(user_id),
        "mode": body.mode,
        "base_url": body.base_url or "",
        "categories": body.categories or ["functional", "edge", "malformed", "security"],
        "intensity": body.intensity,
        "agentic": body.agentic,
        "plan": None,
        "test_cases": [],
        "results": [],
        "errors": [],
        "interrupts": [],
        "human_input": {},
    }

    background_tasks.add_task(run_agentic_pipeline, state)
    return {"session_id": session_id, "id": session_id, "status": "pending"}


@router.get("")
async def list_sessions(
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List sessions for the current user."""
    skip = (page - 1) * page_size
    cursor = get_collection("sessions").find(
        {"user_id": user_id},
        sort=[("created_at", -1)],
        skip=skip,
        limit=page_size,
    )
    docs = await cursor.to_list(length=page_size)
    total = await get_collection("sessions").count_documents({"user_id": user_id})
    sessions = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        d["spec_id"] = str(d["spec_id"])
        d["user_id"] = str(d["user_id"])
        if d.get("provider_profile_id"):
            d["provider_profile_id"] = str(d["provider_profile_id"])
        if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        if d.get("updated_at") and hasattr(d["updated_at"], "isoformat"):
            d["updated_at"] = d["updated_at"].isoformat()
        sessions.append(d)
    return {"sessions": sessions, "total": total, "page": page, "page_size": page_size}


@router.get("/{session_id}")
async def get_session(session_id: str, user_id: CurrentUserId):
    """Get session detail."""
    doc = await get_collection("sessions").find_one({"_id": ObjectId(session_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc["id"] = str(doc.pop("_id"))
    doc["spec_id"] = str(doc["spec_id"])
    doc["user_id"] = str(doc["user_id"])
    if doc.get("provider_profile_id"):
        doc["provider_profile_id"] = str(doc["provider_profile_id"])
    if doc.get("created_at") and hasattr(doc["created_at"], "isoformat"):
        doc["created_at"] = doc["created_at"].isoformat()
    if doc.get("updated_at") and hasattr(doc["updated_at"], "isoformat"):
        doc["updated_at"] = doc["updated_at"].isoformat()
    return doc


@router.get("/{session_id}/events")
async def stream_session_events(
    session_id: str,
    token: str = Query(..., description="JWT token for auth via query param"),
    last_event_id: str | None = Query(None),
):
    """SSE stream of agent events. Uses token query-param since EventSource lacks custom headers."""
    from app.core.security import decode_access_token

    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("no sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Replay past events from DB
    past_cursor = get_collection("agent_events").find(
        {"session_id": session_id},
        sort=[("ts", 1)],
    )
    past_events = await past_cursor.to_list(length=1000)

    queue = subscribe(session_id)

    async def generate() -> AsyncGenerator[str, None]:
        # Replay historical events
        for ev in past_events:
            ev.pop("_id", None)
            data = json.dumps(ev, default=str)
            yield f"data: {data}\n\n"

        # Stream live events
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if event is None:
                    break

                if isinstance(event, AgentEvent):
                    ev_dict = event.to_dict()
                elif isinstance(event, dict):
                    ev_dict = event
                else:
                    ev_dict = {"message": str(event)}

                data = json.dumps(ev_dict, default=str)
                yield f"data: {data}\n\n"
                if ev_dict.get("step") in ("session_done", "session_error"):
                    break
        finally:
            unsubscribe(session_id, queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/approve-plan")
async def approve_plan(
    session_id: str,
    body: PlanApproval,
    background_tasks: BackgroundTasks,
    user_id: CurrentUserId,
):
    """Resume pipeline after plan review."""
    doc = await get_collection("sessions").find_one({"_id": ObjectId(session_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if not doc.get("waiting_human"):
        raise HTTPException(status_code=409, detail="Session is not waiting for human input")

    await get_collection("sessions").update_one(
        {"_id": ObjectId(session_id)},
        {
            "$set": {
                "waiting_human": False,
                "plan_approved": body.approved,
                "status": "running" if body.approved else "cancelled",
            }
        },
    )

    if body.approved:
        state: SessionState = {
            "session_id": session_id,
            "spec_id": str(doc["spec_id"]),
            "user_id": str(user_id),
            "mode": doc.get("mode", "local"),
            "base_url": doc.get("base_url", ""),
            "categories": doc.get("categories", ["functional", "edge", "malformed", "security"]),
            "intensity": doc.get("intensity", "normal"),
            "plan": {"endpoints": body.modified_plan} if body.modified_plan else doc.get("plan"),
            "test_cases": [],
            "results": [],
            "errors": [],
            "interrupts": [],
            "human_input": {"plan_approved": True},
        }
        background_tasks.add_task(resume_after_plan_approval, state)

    return {"status": "ok", "approved": body.approved}


@router.post("/{session_id}/provide-auth")
async def provide_auth(
    session_id: str,
    body: AuthProvision,
    user_id: CurrentUserId,
):
    """Store an auth token (encrypted) for mid-run auth prompts."""
    doc = await get_collection("sessions").find_one({"_id": ObjectId(session_id), "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    encrypted = encrypt_value(body.token)

    await get_collection("sessions").update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"auth_token_encrypted": encrypted, "waiting_human": False}},
    )
    return {"status": "ok"}


@router.post("/{session_id}/cancel")
async def cancel_session(session_id: str, user_id: CurrentUserId):
    """Cancel a running session."""
    result = await get_collection("sessions").update_one(
        {
            "_id": ObjectId(session_id),
            "user_id": user_id,
            "status": {"$in": ["pending", "waiting_approval", "running"]},
        },
        {"$set": {"status": "cancelled", "updated_at": datetime.datetime.now(datetime.UTC)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found or not cancellable")
    return {"status": "cancelled"}
