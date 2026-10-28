"""AgentEvent model and in-process pub/sub for SSE delivery."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import structlog

logger = structlog.get_logger()

# In-process pub/sub: session_id → list of subscriber queues
_subscribers: dict[str, list[asyncio.Queue]] = {}


@dataclass
class AgentEvent:
    session_id: str
    agent: str
    step: str
    status: Literal["started", "progress", "completed", "completed_with_errors", "failed", "waiting_human"]
    message: str
    ts: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Any = None
    tokens: int = 0
    latency_ms: int = 0
    provider: str | None = None
    model: str | None = None
    rag_used: bool = False
    rag_sources: list[dict] = field(default_factory=list)
    repairs_used: int = 0
    event_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent": self.agent,
            "step": self.step,
            "status": self.status,
            "message": self.message,
            "ts": self.ts,
            "data": self.data,
            "tokens": self.tokens,
            "latency_ms": self.latency_ms,
            "provider": self.provider,
            "model": self.model,
            "rag_used": self.rag_used,
            "rag_sources": self.rag_sources,
            "repairs_used": self.repairs_used,
            "event_id": self.event_id,
        }


def subscribe(session_id: str) -> asyncio.Queue:
    """Create a new subscriber queue for a session."""
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers.setdefault(session_id, []).append(q)
    return q


def unsubscribe(session_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(session_id, [])
    if q in subs:
        subs.remove(q)


async def publish(event: AgentEvent) -> None:
    """Persist an event before publishing it to local SSE subscribers."""
    try:
        from app.db.mongo import get_collection

        col = get_collection("agent_events")
        payload = event.to_dict()
        payload.pop("event_id", None)
        result = await col.insert_one(payload)
        event.event_id = str(result.inserted_id)
    except Exception as e:
        logger.warning("Failed to persist agent event", error=str(e))

    subs = _subscribers.get(event.session_id, [])
    for q in list(subs):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Subscriber queue full, dropping event", session_id=event.session_id)
