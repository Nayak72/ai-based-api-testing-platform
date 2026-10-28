"""TriageAgent — classifies each failed result as real_bug/test_bug/spec_drift/flaky/ok."""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.agents.state import SessionState

logger = structlog.get_logger()


class TriageAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("triage")

    async def run(self, state: SessionState) -> SessionState:
        await self.emit(state, "triage", "started", "Triaging test results...")

        run_id = state.get("run_id")
        if not run_id:
            await self.emit(state, "triage", "completed", "No run to triage")
            return state

        try:
            from bson import ObjectId

            from app.db.repositories import result_repository

            results = await result_repository.list_by_run(ObjectId(run_id), limit=10000)
            failed = [r for r in results if r.status in ("failed", "error")]

            await self.emit(state, "triage", "progress", f"Classifying {len(failed)} non-passing results...")

            triage_results = []
            for result in failed:
                # Deterministic heuristic triage (LLM-enhanced triage can be added later)
                verdict = self._heuristic_verdict(result)
                owasp_cat = None
                if result.llm_analysis:
                    owasp_cat = result.llm_analysis.owasp_category
                risk = result.llm_analysis.risk_level if result.llm_analysis else "medium"

                triage_results.append(
                    {
                        "result_id": str(result.id),
                        "endpoint_id": result.endpoint_id,
                        "category": result.category,
                        "verdict": verdict,
                        "risk_level": risk,
                        "owasp_category": owasp_cat,
                        "evidence": f"Status: {result.status}; Response: {result.response.status_code}",
                        "recommendation": self._recommendation(verdict),
                        "rag_sources": [],
                    }
                )

            state["triage"] = triage_results
            bugs = sum(1 for t in triage_results if t["verdict"] == "real_bug")
            await self.emit(
                state,
                "triage",
                "completed",
                f"Triage done: {bugs} real bugs found in {len(triage_results)} results",
                data={"triage_count": len(triage_results), "real_bugs": bugs},
            )
            return state

        except Exception as e:
            logger.exception("TriageAgent failed", error=str(e))
            state.setdefault("errors", []).append(f"TriageAgent: {e}")
            await self.emit(state, "triage", "failed", str(e))
            return state

    @staticmethod
    def _heuristic_verdict(result) -> str:
        """Simple heuristic: classify based on category and response."""
        if result.status == "error":
            return "environment"
        if result.category == "security" and result.response.status_code in (200, 201):
            return "real_bug"
        if result.category in ("functional",) and result.response.status_code >= 500:
            return "real_bug"
        if result.category == "malformed" and result.response.status_code >= 500:
            return "real_bug"
        if result.response.status_code == 200 and result.category == "edge":
            return "test_bug"
        return "real_bug"

    @staticmethod
    def _recommendation(verdict: str) -> str:
        return {
            "real_bug": "Fix the vulnerability in the API implementation and re-test.",
            "test_bug": "Review and correct the test case — the API may be working correctly.",
            "spec_drift": "Update the API spec to match the actual implementation.",
            "flaky": "Re-run to confirm; may be a transient network or timing issue.",
            "environment": "Check network connectivity and target availability.",
            "ok": "No action needed.",
        }.get(verdict, "Manual review recommended.")
