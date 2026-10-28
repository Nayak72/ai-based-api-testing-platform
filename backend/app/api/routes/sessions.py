"""Session routes — agentic pipeline sessions with SSE event streaming."""

from __future__ import annotations

import asyncio
import datetime
import json
from collections.abc import AsyncGenerator

import structlog
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agents.events import AgentEvent, subscribe, unsubscribe
from app.agents.graph import resume_after_plan_approval, run_agentic_pipeline
from app.agents.state import SessionState
from app.api.deps import CurrentUser, CurrentUserId
from app.api.ids import parse_object_id
from app.core.security import encrypt_value
from app.db.mongo import get_collection
from app.db.repositories import provider_repository, spec_repository
from app.safety.target_guard import TargetPolicy, TargetGuard

logger = structlog.get_logger()
router = APIRouter()


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_id: str
    name: str = Field(min_length=1, max_length=200)
    mode: TargetPolicy = TargetPolicy.LOCAL
    base_url: str | None = None
    auth_type: Literal["bearer", "api_key"] | None = None
    auth_token: str | None = None
    secondary_auth_type: Literal["bearer", "api_key"] | None = None
    secondary_auth_token: str | None = None
    provider_profile_id: str | None = None
    categories: list[Literal["functional", "edge", "malformed", "security"]] = Field(
        default_factory=lambda: ["functional", "edge", "malformed", "security"]
    )
    intensity: Literal["safe", "standard", "aggressive"] = "standard"
    owned_host_attestation: bool = False
    agentic: Literal[True] = True

    @field_validator("categories")
    @classmethod
    def require_categories(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one test category is required")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_safety_settings(self) -> "SessionCreate":
        if self.mode == TargetPolicy.ONLINE and "security" in self.categories and not self.owned_host_attestation:
            raise ValueError("Online security testing requires ownership attestation")
        if bool(self.auth_type) != bool(self.auth_token):
            raise ValueError("auth_type and auth_token must be provided together")
        if bool(self.secondary_auth_type) != bool(self.secondary_auth_token):
            raise ValueError("secondary_auth_type and secondary_auth_token must be provided together")
        return self


class PlanApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool
    modified_plan: list[dict] | None = None


class AuthProvision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str


@router.post("", status_code=201)
async def create_session(
    body: SessionCreate,
    background_tasks: BackgroundTasks,
    user_id: CurrentUserId,
):
    """Create a new agentic test session."""
    spec_id = parse_object_id(body.spec_id, "spec")
    spec = await spec_repository.get_by_id(spec_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    if spec.status != "ready" or not spec.parsed_spec:
        raise HTTPException(status_code=409, detail="Spec is not ready for testing")

    provider_profile_id = None
    if body.provider_profile_id:
        provider_profile_id = parse_object_id(body.provider_profile_id, "provider profile")
        if not await provider_repository.get_by_id(provider_profile_id, user_id):
            raise HTTPException(status_code=404, detail="Provider profile not found")

    effective_base_url = body.base_url or spec.base_url
    if not effective_base_url:
        raise HTTPException(status_code=422, detail="A target base URL is required")
    guard = TargetGuard(mode=body.mode)
    decision = guard.check(effective_base_url, body.mode, guard.owned_allowlist)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=f"Target blocked: {decision.reason}")

    try:
        auth_token_encrypted = encrypt_value(body.auth_token) if body.auth_token else None
        secondary_auth_token_encrypted = encrypt_value(body.secondary_auth_token) if body.secondary_auth_token else None
    except Exception as exc:
        logger.error("Session secret encryption failed", error=type(exc).__name__)
        raise HTTPException(status_code=503, detail="Session credentials could not be stored securely") from exc

    now = datetime.datetime.now(datetime.UTC)
    doc = {
        "spec_id": spec_id,
        "user_id": user_id,
        "name": body.name,
        "status": "pending",
        "mode": body.mode,
        "base_url": effective_base_url,
        "auth_type": body.auth_type,
        "auth_token_encrypted": auth_token_encrypted,
        "secondary_auth_type": body.secondary_auth_type,
        "secondary_auth_token_encrypted": secondary_auth_token_encrypted,
        "provider_profile_id": provider_profile_id,
        "categories": body.categories,
        "intensity": body.intensity,
        "agentic": body.agentic,
        "owned_host_attestation": body.owned_host_attestation,
        "created_at": now,
        "updated_at": now,
    }
    result = await get_collection("sessions").insert_one(doc)
    session_id = str(result.inserted_id)

    state: SessionState = {
        "session_id": session_id,
        "spec_id": str(spec_id),
        "user_id": str(user_id),
        "mode": body.mode.value,
        "base_url": effective_base_url,
        "categories": body.categories,
        "intensity": body.intensity,
        "agentic": body.agentic,
        "owned_host_attestation": body.owned_host_attestation,
        "routing": {"provider_profile_id": str(provider_profile_id)} if provider_profile_id else {},
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
        d.pop("auth_token_encrypted", None)
        d.pop("secondary_auth_token_encrypted", None)
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
    session_obj_id = parse_object_id(session_id, "session")
    doc = await get_collection("sessions").find_one({"_id": session_obj_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc["id"] = str(doc.pop("_id"))
    doc.pop("auth_token_encrypted", None)
    doc.pop("secondary_auth_token_encrypted", None)
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
    current_user: CurrentUser,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
):
    """Owner-scoped SSE stream authenticated by access cookie or bearer header."""
    session_obj_id = parse_object_id(session_id, "session")
    session = await get_collection("sessions").find_one({"_id": session_obj_id, "user_id": current_user.id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event_query: dict = {"session_id": session_id}
    if last_event_id:
        event_query["_id"] = {"$gt": parse_object_id(last_event_id, "event")}
    # Subscribe first so events emitted while the durable history is replayed
    # remain observable. IDs are deduplicated in the generator below.
    queue = subscribe(session_id)
    past_cursor = get_collection("agent_events").find(event_query, sort=[("_id", 1)])
    past_events = await past_cursor.to_list(length=1000)

    async def generate() -> AsyncGenerator[str, None]:
        emitted_ids: set[str] = set()

        def frame(ev: dict) -> str:
            event_id = str(ev.pop("_id", ev.get("event_id", "")))
            ev["event_id"] = event_id
            emitted_ids.add(event_id)
            return f"id: {event_id}\ndata: {json.dumps(ev, default=str)}\n\n"

        for ev in past_events:
            yield frame(ev)

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

                event_id = ev_dict.get("event_id")
                if event_id and event_id in emitted_ids:
                    continue
                yield frame(ev_dict)
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
    session_obj_id = parse_object_id(session_id, "session")
    doc = await get_collection("sessions").find_one({"_id": session_obj_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if not doc.get("waiting_human") or doc.get("status") != "waiting_approval":
        raise HTTPException(status_code=409, detail="Session is not waiting for human input")

    update = await get_collection("sessions").update_one(
        {"_id": session_obj_id, "user_id": user_id, "waiting_human": True, "status": "waiting_approval"},
        {
            "$set": {
                "waiting_human": False,
                "plan_approved": body.approved,
                "status": "running" if body.approved else "cancelled",
            }
        },
    )
    if update.modified_count != 1:
        raise HTTPException(status_code=409, detail="Session approval was already processed")

    if body.approved:
        state: SessionState = {
            "session_id": session_id,
            "spec_id": str(doc["spec_id"]),
            "user_id": str(user_id),
            "mode": doc.get("mode", "local"),
            "base_url": doc.get("base_url", ""),
            "categories": doc.get("categories", ["functional", "edge", "malformed", "security"]),
            "intensity": doc.get("intensity", "standard"),
            "owned_host_attestation": doc.get("owned_host_attestation", False),
            "routing": {"provider_profile_id": str(doc["provider_profile_id"])} if doc.get("provider_profile_id") else {},
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
    session_obj_id = parse_object_id(session_id, "session")
    doc = await get_collection("sessions").find_one({"_id": session_obj_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        encrypted = encrypt_value(body.token)
    except Exception as exc:
        logger.error("Session secret encryption failed", error=type(exc).__name__)
        raise HTTPException(status_code=503, detail="Credentials could not be stored securely") from exc

    await get_collection("sessions").update_one(
        {"_id": session_obj_id, "user_id": user_id},
        {"$set": {"auth_token_encrypted": encrypted, "waiting_human": False}},
    )
    return {"status": "ok"}


@router.post("/{session_id}/cancel")
async def cancel_session(session_id: str, user_id: CurrentUserId):
    """Cancel a running session."""
    session_obj_id = parse_object_id(session_id, "session")
    result = await get_collection("sessions").update_one(
        {
            "_id": session_obj_id,
            "user_id": user_id,
            "status": {"$in": ["pending", "ingesting", "planning", "waiting_approval", "running"]},
        },
        {"$set": {"status": "cancelled", "updated_at": datetime.datetime.now(datetime.UTC)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found or not cancellable")
    return {"status": "cancelled"}
