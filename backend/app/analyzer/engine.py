import json
from datetime import UTC, datetime

import structlog
from bson import ObjectId

from app.ai import GenerationRequest, ProviderError, create_orchestrator
from app.db.models import LLMAnalysis, TestResultInDB
from app.db.repositories import result_repository
from app.db.mongo import get_collection

logger = structlog.get_logger()


class ResultAnalyzer:
    def __init__(
        self,
        primary_provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.ai = create_orchestrator(
            primary_provider=primary_provider,
            model=model,
            api_key=api_key,
        )
        self._initialized = True

    async def analyze_run(self, run_id: ObjectId):
        run_collection = get_collection("test_runs")
        completed = errors = 0
        try:
            results = await result_repository.list_by_run(run_id, limit=10000)
            candidates = [r for r in results if r.status in ("passed", "failed") and not r.llm_analysis]
            logger.info("Starting analysis", run_id=str(run_id), results=len(candidates))

            for result in candidates:
                try:
                    analysis = await self.analyze_result(result)
                    await result_repository.update_analysis(result.id, analysis.model_dump())
                    if analysis.risk_level == "unknown":
                        errors += 1
                except Exception as exc:
                    errors += 1
                    logger.exception("Analysis failed for result", result_id=str(result.id))
                    fallback = LLMAnalysis(
                        risk_level="unknown",
                        summary="Analysis could not be completed; review this result manually.",
                        findings=[{"type": "analysis_error", "description": str(exc), "evidence": ""}],
                        recommendations=["Retry analysis or review the test result manually."],
                        false_positive_likelihood=0.5,
                    )
                    await result_repository.update_analysis(result.id, fallback.model_dump())
                finally:
                    completed += 1
                    await run_collection.update_one(
                        {"_id": run_id},
                        {"$set": {"analysis_completed": completed, "analysis_error_count": errors}},
                    )

            status = "completed_with_errors" if errors else "completed"
            await run_collection.update_one(
                {"_id": run_id},
                {"$set": {"analysis_status": status, "analysis_completed": completed,
                           "analysis_error_count": errors, "analysis_completed_at": datetime.now(UTC)}},
            )
            logger.info("Analysis completed", run_id=str(run_id), analyzed=completed, errors=errors)
        except Exception as exc:
            logger.exception("Run analysis worker failed", run_id=str(run_id))
            await run_collection.update_one(
                {"_id": run_id},
                {"$set": {"analysis_status": "failed", "analysis_error": str(exc),
                           "analysis_error_count": errors + 1, "analysis_completed_at": datetime.now(UTC)}},
            )
        finally:
            await self.close()

    async def analyze_result(self, result: TestResultInDB) -> LLMAnalysis:
        prompt = self._build_analysis_prompt(result)

        request = GenerationRequest(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            temperature=0.1,
            max_tokens=2048,
            response_format="json_object",
        )

        try:
            response = await self.ai.generate(request)
            return self._parse_analysis(response.content)
        except ProviderError as e:
            logger.error("Analysis LLM call failed", error=str(e))
            return LLMAnalysis(
                risk_level="unknown",
                summary="Analysis failed due to LLM error",
                findings=[{"type": "error", "description": str(e), "evidence": ""}],
                recommendations=["Manual review required"],
                false_positive_likelihood=0.5,
            )

    def _get_system_prompt(self) -> str:
        return """You are an expert API security analyst. Analyze test results and provide structured risk assessment. Output STRICT JSON only.

Schema:
{
  "risk_level": "low|medium|high|critical",
  "summary": "string",
  "findings": [{"type": "security|functional|performance", "description": "string", "evidence": "string"}],
  "recommendations": ["string"],
  "false_positive_likelihood": 0.0-1.0
}"""

    def _build_analysis_prompt(self, result: TestResultInDB) -> str:
        return f"""Analyze this API test result:

Test Case: {result.endpoint_id} ({result.category})
Status: {result.status}
Request: {result.request_sent.model_dump_json()}
Response Status: {result.response.status_code}
Response Headers: {result.response.headers}
Response Body: {result.response.body}
Duration: {result.response.duration_ms}ms
Assertions: {json.dumps([a.assertion.model_dump() for a in result.assertions])}
Assertion Results: {[a.result for a in result.assertions]}

Provide risk assessment following the schema."""

    def _parse_analysis(self, content: str) -> LLMAnalysis:
        try:
            data = json.loads(content)
            return LLMAnalysis(
                risk_level=data.get("risk_level", "low"),
                summary=data.get("summary", ""),
                findings=data.get("findings", []),
                recommendations=data.get("recommendations", []),
                false_positive_likelihood=data.get("false_positive_likelihood", 0.1),
            )
        except json.JSONDecodeError:
            return LLMAnalysis(
                risk_level="unknown",
                summary="Failed to parse analysis response",
                findings=[],
                recommendations=["Manual review required"],
                false_positive_likelihood=0.5,
            )

    async def close(self) -> None:
        if self._initialized and self.ai and hasattr(self.ai, "providers"):
            for provider in self.ai.providers:
                if provider and hasattr(provider, "close"):
                    await provider.close()
