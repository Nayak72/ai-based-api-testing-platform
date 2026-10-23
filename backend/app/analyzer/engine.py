import json

import structlog
from bson import ObjectId

from app.ai import AIOrchestrator, GenerationRequest, ProviderError
from app.db.models import LLMAnalysis, TestResultInDB
from app.db.repositories import result_repository

logger = structlog.get_logger()


class ResultAnalyzer:
    def __init__(self):
        self.ai: AIOrchestrator | None = None
        self._initialized = False

    async def _ensure_initialized(self):
        if not self._initialized or self.ai is None:
            from app.ai import create_orchestrator
            self.ai = create_orchestrator()
            self._initialized = True

    async def analyze_run(self, run_id: ObjectId):
        await self._ensure_initialized()

        results = await result_repository.list_by_run(run_id, limit=10000)
        logger.info("Starting analysis", run_id=str(run_id), results=len(results))

        for result in results:
            if result.status in ("passed", "failed") and not result.llm_analysis:
                try:
                    analysis = await self.analyze_result(result)
                    await result_repository.update_analysis(result.id, analysis.model_dump())
                except Exception as e:
                    logger.error("Analysis failed for result", result_id=str(result.id), error=str(e))

        logger.info("Analysis completed", run_id=str(run_id))

    async def analyze_result(self, result: TestResultInDB) -> LLMAnalysis:
        await self._ensure_initialized()
        prompt = self._build_analysis_prompt(result)

        request = GenerationRequest(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            temperature=0.1,
            max_tokens=2048,
            response_format="json_object",
        )

        try:
            if self.ai is None:
                raise ProviderError(code="not_initialized", message="AI Orchestrator not initialized")
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
