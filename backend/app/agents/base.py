"""BaseAgent — wraps LLM calls with event emission, routing, cancellation."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import structlog

from app.agents.events import AgentEvent, publish
from app.agents.state import SessionState

logger = structlog.get_logger()


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def run(self, state: SessionState) -> SessionState:
        """Execute the agent. Return updated state."""
        ...

    async def emit(self, state: SessionState, step: str, status: str, message: str, **kwargs) -> None:
        event = AgentEvent(
            session_id=state.get("session_id", ""),
            agent=self.name,
            step=step,
            status=status,
            message=message,
            **kwargs,
        )
        await publish(event)

    def _get_ai(self, state: SessionState):
        """Get AI orchestrator from routing config or default."""
        from app.ai import create_orchestrator

        routing = state.get("routing", {})
        primary = routing.get("cloud_profile_id") or routing.get("primary_provider")
        return create_orchestrator(primary_provider=primary)

    async def llm(self, state: SessionState, prompt: str, system: str, model_cls=None, model: str | None = None):
        """LLM call wrapper with structured output if model_cls provided."""
        ai = self._get_ai(state)
        start = time.perf_counter()
        try:
            if model_cls:
                from app.ai.structured import generate_structured

                result = await generate_structured(ai, prompt=prompt, system=system, model_cls=model_cls, model=model)
                latency_ms = int((time.perf_counter() - start) * 1000)
                return result, latency_ms
            else:
                from app.ai.providers.base import GenerationRequest

                req = GenerationRequest(
                    prompt=prompt,
                    system_prompt=system,
                    temperature=0.1,
                    max_tokens=4096,
                    response_format="json_object",
                    model=model,
                )
                resp = await ai.generate(req)
                latency_ms = int((time.perf_counter() - start) * 1000)
                return resp.content, latency_ms
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.error("LLM call failed in agent", agent=self.name, error=str(e))
            raise
