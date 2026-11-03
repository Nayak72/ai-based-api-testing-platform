import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path

import structlog
from bson import ObjectId
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ai import AIOrchestrator, GenerationRequest, ProviderError
from app.config import get_settings
from app.db.models import (
    ExpectedResponse,
    GenerationCache,
    RequestTemplate,
    TestCaseCreate,
    TestCaseMetadata,
)
from app.db.repositories import generation_cache_repository

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent / "prompts"


class BaseGenerator(ABC):
    CATEGORY: str = ""
    SUBCATEGORIES: list[str] = []
    PROMPT_VERSION: str = "v1"

    def __init__(self, ai_orchestrator: AIOrchestrator) -> None:
        self.ai = ai_orchestrator
        self.settings = get_settings()
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @abstractmethod
    def get_system_prompt(self) -> str: ...

    @abstractmethod
    def get_prompt_template_name(self) -> str: ...

    @abstractmethod
    def parse_response(self, content: str, endpoint_id: str, spec_id: ObjectId) -> list[TestCaseCreate]: ...

    def _build_prompt(self, endpoint: dict, spec: dict, subcategory: str) -> str:
        template = self.jinja_env.get_template(self.get_prompt_template_name())
        return template.render(
            endpoint=endpoint,
            spec=spec,
            category=self.CATEGORY,
            subcategory=subcategory,
            max_tests_per_call=self.settings.max_tests_per_call,
        ) + f"\nReturn no more than {self.settings.max_tests_per_call} test cases."

    def _compute_prompt_hash(self, prompt: str) -> str:
        return f"sha256:{hashlib.sha256(prompt.encode()).hexdigest()}"

    @classmethod
    def _parse_test_cases(
        cls,
        content: str,
        endpoint_id: str,
        spec_id: ObjectId,
        category: str,
        subcategory_default: str,
        owasp_mapping: dict | None = None,
    ) -> list[TestCaseCreate]:
        """Shared parser for all generators. Reduces duplication across functional.py."""
        data = cls._parse_json_response(content)
        items = data if isinstance(data, list) else data.get("test_cases", [])
        test_cases = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            try:
                subcat = item.get("subcategory", subcategory_default)
                metadata = item.get("metadata") or {}
                owasp = (owasp_mapping or {}).get(subcat) or metadata.get("owasp_category")
                request_data = item.get("request") or {}
                expected_data = item.get("expected") or {}
                method = str(request_data.get("method") or "GET").upper()
                path = str(request_data.get("path") or "/")
                assertion_items = expected_data.get("assertions") or []
                assertions = []
                for assertion in assertion_items:
                    if not isinstance(assertion, dict):
                        continue
                    assertion_type = str(assertion.get("type") or "").lower()
                    if assertion_type == "body":
                        assertion_type = "json_path"
                    if assertion_type not in {"status_code", "header", "json_path", "schema", "response_time"}:
                        continue
                    operator = str(assertion.get("operator") or ("eq" if assertion_type == "status_code" else "exists")).lower()
                    assertions.append({
                        "type": assertion_type,
                        "path": assertion.get("path") or ("$" if assertion_type == "json_path" else ""),
                        "operator": operator,
                        "value": assertion.get("value"),
                    })
                tc = TestCaseCreate(
                    spec_id=spec_id,
                    endpoint_id=endpoint_id,
                    category=category,
                    subcategory=subcat,
                    title=str(item.get("title") or f"{category} test {index + 1}"),
                    description=str(item.get("description") or "Generated API test case"),
                    request=RequestTemplate(
                        method=method,
                        path=path,
                        headers=request_data.get("headers") or {},
                        query_params=request_data.get("query_params") or request_data.get("query") or {},
                        body=request_data.get("body"),
                        raw_body=request_data.get("raw_body"),
                        content_type=request_data.get("content_type"),
                    ),
                    expected=ExpectedResponse(
                        status_code=int(expected_data.get("status_code") or 200),
                        response_schema=expected_data.get("response_schema") or expected_data.get("schema"),
                        assertions=assertions,
                    ),
                    metadata=TestCaseMetadata(
                        owasp_category=owasp,
                        severity=metadata.get("severity", "medium"),
                        generated_by="",
                        generation_prompt_hash="",
                        tokens_used=0,
                        request_hash="",
                    ),
                )
                test_cases.append(tc)
            except Exception as exc:
                logger.warning("Dropping invalid generated test case", endpoint_id=endpoint_id, error=str(exc))
        if not test_cases:
            raise ValueError("Generator response contained no valid test cases")
        return test_cases

    def _compute_request_hash(self, request: dict) -> str:
        normalized = json.dumps(request, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()}"

    @staticmethod
    def _parse_json_response(content: str) -> dict | list:
        """Parse provider output while tolerating common LLM JSON damage."""
        try:
            import json_repair

            value = json_repair.loads(content)
            if isinstance(value, (dict, list)):
                return value
        except Exception:
            pass

        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()
        value = json.loads(cleaned)
        if not isinstance(value, (dict, list)):
            raise ValueError("Generator response must be a JSON object or array")
        return value

    async def generate_for_endpoint(
        self,
        spec_id: ObjectId,
        endpoint: dict,
        spec: dict,
        subcategory: str,
        model: str | None = None,
        session_id: str | None = None,
        unit_id: str | None = None,
        prompt_version: str | None = None,
    ) -> list[TestCaseCreate]:
        resolved_prompt_version = prompt_version or self.PROMPT_VERSION
        cached = await generation_cache_repository.get(
            spec_id, endpoint["endpoint_id"], self.CATEGORY, resolved_prompt_version, model, subcategory
        )
        if cached:
            logger.info(
                "Cache hit",
                spec_id=str(spec_id),
                endpoint_id=endpoint["endpoint_id"],
                category=self.CATEGORY,
                model=model,
            )
            return [TestCaseCreate(**tc) for tc in cached.test_cases]

        prompt = self._build_prompt(endpoint, spec, subcategory)
        prompt_hash = self._compute_prompt_hash(prompt)

        request = GenerationRequest(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.1,
            max_tokens=self.settings.ai_max_output_tokens,
            response_format="json_object",
            model=model,
        )

        try:
            response = await self.ai.generate(request, validator=lambda result: self.parse_response(
                result.content, endpoint["endpoint_id"], spec_id
            ))
        except ProviderError as e:
            logger.exception(
                "Generation failed", category=self.CATEGORY, endpoint_id=endpoint["endpoint_id"], error=str(e)
            )
            raise

        response, test_cases = response

        for tc in test_cases:
            tc.metadata = TestCaseMetadata(
                owasp_category=tc.metadata.owasp_category,
                severity=tc.metadata.severity,
                generated_by=response.provider.value,
                generation_prompt_hash=prompt_hash,
                tokens_used=response.tokens_used,
                request_hash=self._compute_request_hash(tc.request.model_dump()),
            )

        cache_entry = GenerationCache(
            spec_id=spec_id,
            endpoint_id=endpoint["endpoint_id"],
            category=self.CATEGORY,
            prompt_version=resolved_prompt_version,
            subcategory=subcategory,
            prompt_hash=prompt_hash,
            spec_hash=spec.get("spec_hash", ""),
            test_cases=[tc.model_dump() for tc in test_cases],
            tokens_used=response.tokens_used,
            provider=response.provider.value,
            model=response.model,
        )

        await generation_cache_repository.set(cache_entry)

        logger.info(
            "Generation completed",
            category=self.CATEGORY,
            endpoint_id=endpoint["endpoint_id"],
            test_cases=len(test_cases),
            tokens=response.tokens_used,
        )
        return test_cases
