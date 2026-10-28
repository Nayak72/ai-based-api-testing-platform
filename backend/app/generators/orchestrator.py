import structlog

from app.ai import create_orchestrator
from app.generators.functional import (
    EdgeGenerator,
    FunctionalGenerator,
    MalformedGenerator,
    SecurityGenerator,
)
from app.parsers import extract_endpoints

logger = structlog.get_logger()


class GenerationOrchestrator:
    def __init__(
        self,
        primary_provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.ai_orchestrator = create_orchestrator(
            primary_provider=primary_provider,
            model=model,
            api_key=api_key,
        )
        self.generators = {
            "functional": FunctionalGenerator(self.ai_orchestrator),
            "edge": EdgeGenerator(self.ai_orchestrator),
            "malformed": MalformedGenerator(self.ai_orchestrator),
            "security": SecurityGenerator(self.ai_orchestrator),
        }

    async def generate_for_spec(
        self,
        spec_id: str,
        user_id: str,
        categories: list[str],
        prompt_version: str = "v1",
        dry_run: bool = False,
        model: str | None = None,
    ):
        from bson import ObjectId

        from app.db.repositories import spec_repository, test_case_repository

        target_model = model or self.model

        spec = await spec_repository.get_by_id(ObjectId(spec_id), ObjectId(user_id))
        if not spec or not spec.parsed_spec:
            logger.error("Spec not found or not parsed", spec_id=spec_id)
            return

        endpoints = extract_endpoints(spec.parsed_spec)
        logger.info(
            "Starting generation", spec_id=spec_id, endpoints=len(endpoints), categories=categories, model=target_model
        )

        for endpoint in endpoints:
            for category in categories:
                if category not in self.generators:
                    continue
                generator = self.generators[category]
                generator.PROMPT_VERSION = prompt_version

                try:
                    test_cases = await generator.generate_for_endpoint(
                        spec_id=ObjectId(spec_id),
                        endpoint=endpoint,
                        spec=spec.parsed_spec,
                        subcategory=generator.SUBCATEGORIES[0],
                        model=target_model,
                    )

                    if not dry_run and test_cases:
                        await test_case_repository.bulk_upsert(test_cases)
                        logger.info("Test cases saved", count=len(test_cases), category=category)

                except Exception as e:
                    logger.error(
                        "Generation failed for endpoint",
                        endpoint_id=endpoint["endpoint_id"],
                        category=category,
                        error=str(e),
                    )

        logger.info("Generation completed", spec_id=spec_id)

    async def close(self) -> None:
        for provider in self.ai_orchestrator.providers:
            if provider and hasattr(provider, "close"):
                await provider.close()
