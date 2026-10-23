import hashlib
import json
from abc import ABC, abstractmethod

import structlog
from bson import ObjectId
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ai import AIOrchestrator, GenerationRequest, ProviderError
from app.config import get_settings
from app.db.models import GenerationCache, TestCaseCreate, TestCaseMetadata
from app.db.repositories import generation_cache_repository

logger = structlog.get_logger()


class BaseGenerator(ABC):
    CATEGORY: str = ""
    SUBCATEGORIES: list[str] = []
    PROMPT_VERSION: str = "v1"

    def __init__(self, ai_orchestrator: AIOrchestrator) -> None:
        self.ai = ai_orchestrator
        self.settings = get_settings()
        self.jinja_env = Environment(
            loader=FileSystemLoader("backend/app/generators/prompts"),
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

    def _build_prompt(self, endpoint: dict, spec: dict) -> str:
        template = self.jinja_env.get_template(self.get_prompt_template_name())
        return template.render(endpoint=endpoint, spec=spec, category=self.CATEGORY)

    def _compute_prompt_hash(self, prompt: str) -> str:
        return f"sha256:{hashlib.sha256(prompt.encode()).hexdigest()}"

    def _compute_request_hash(self, request: dict) -> str:
        normalized = json.dumps(request, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(normalized.encode()).hexdigest()}"

    async def generate_for_endpoint(
        self,
        spec_id: ObjectId,
        endpoint: dict,
        spec: dict,
        subcategory: str,
        model: str | None = None,
    ) -> list[TestCaseCreate]:
        cached = await generation_cache_repository.get(spec_id, endpoint["endpoint_id"], self.CATEGORY, self.PROMPT_VERSION, model)
        if cached:
            logger.info("Cache hit", spec_id=str(spec_id), endpoint_id=endpoint["endpoint_id"], category=self.CATEGORY, model=model)
            return [TestCaseCreate(**tc) for tc in cached.test_cases]

        prompt = self._build_prompt(endpoint, spec)
        prompt_hash = self._compute_prompt_hash(prompt)

        request = GenerationRequest(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.1,
            max_tokens=4096,
            response_format="json_object",
            model=model,
        )

        try:
            response = await self.ai.generate(request)
        except ProviderError as e:
            logger.exception("Generation failed", category=self.CATEGORY, endpoint_id=endpoint["endpoint_id"], error=str(e))
            raise

        test_cases = self.parse_response(response.content, endpoint["endpoint_id"], spec_id)

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
            prompt_version=self.PROMPT_VERSION,
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
