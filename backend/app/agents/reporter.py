"""ReporterAgent — generates the final HTML/PDF/JSON report."""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.agents.state import SessionState

logger = structlog.get_logger()


class ReporterAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("reporter")

    async def run(self, state: SessionState) -> SessionState:
        await self.emit(state, "report", "started", "Generating final report...")

        run_id = state.get("run_id")
        user_id = state.get("user_id")

        if not run_id or not user_id:
            await self.emit(state, "report", "completed", "No run to report (skipping)")
            return state

        try:
            from bson import ObjectId

            from app.reports.generator import ReportGenerator

            generator = ReportGenerator()
            await generator.generate(ObjectId(run_id), ObjectId(user_id), format="both")

            await self.emit(
                state,
                "report",
                "completed",
                "Report generated (HTML + PDF)",
                data={"run_id": run_id},
            )
            return state

        except Exception as e:
            logger.exception("ReporterAgent failed", error=str(e))
            state.setdefault("errors", []).append(f"ReporterAgent: {e}")
            await self.emit(state, "report", "failed", str(e))
            return state
