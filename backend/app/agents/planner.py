"""PlannerAgent — decides which categories to test per endpoint using RAG."""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.agents.state import SessionState

logger = structlog.get_logger()


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("planner")

    async def run(self, state: SessionState) -> SessionState:
        await self.emit(state, "plan", "started", "Planning test strategy...")
        try:
            from bson import ObjectId
            from app.db.repositories import spec_repository
            from app.parsers import extract_endpoints

            spec_id = state.get("spec_id", "")
            user_id = state.get("user_id", "")
            mode = state.get("mode", "local")
            categories = state.get("categories", ["functional", "edge", "malformed", "security"])

            spec = await spec_repository.get_by_id(ObjectId(spec_id), ObjectId(user_id))

            if not spec or not spec.parsed_spec:
                state.setdefault("errors", []).append("Spec not found or not parsed")
                await self.emit(state, "plan", "failed", "Spec not found or not parsed")
                return state

            endpoints = extract_endpoints(spec.parsed_spec)

            # Filter categories based on mode
            if mode == "online" and not state.get("owned_host_attestation"):
                categories = [c for c in categories if c not in ("security", "resource_consumption")]

            # Build plan (deterministic default + optional LLM enhancement)
            plan_endpoints = []
            for ep in endpoints:
                plan_endpoints.append(
                    {
                        "endpoint_id": ep["endpoint_id"],
                        "method": ep["method"],
                        "path": ep["path"],
                        "categories": categories,
                        "priority": "medium",
                        "needs_auth": bool(ep.get("operation", {}).get("security")),
                        "depends_on": [],
                        "notes": "",
                    }
                )

            state["plan"] = {"endpoints": plan_endpoints, "categories": categories}

            # Interrupt for human approval
            state.setdefault("interrupts", []).append("approve_plan")

            await self.emit(
                state,
                "plan",
                "waiting_human",
                f"Plan ready: {len(plan_endpoints)} endpoints. Awaiting approval.",
                data=state["plan"],
            )
            return state

        except Exception as e:
            logger.exception("PlannerAgent failed", error=str(e))
            state.setdefault("errors", []).append(f"PlannerAgent: {e}")
            await self.emit(state, "plan", "failed", str(e))
            return state
