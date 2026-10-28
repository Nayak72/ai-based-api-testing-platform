import structlog

from app.ai.providers.base import (
    AIProvider,
    GenerationRequest,
    GenerationResponse,
    ProviderError,
    ProviderName,
)
from app.ai.providers.nim import NIMProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.config import get_settings

logger = structlog.get_logger()


class AIOrchestrator:
    def __init__(
        self,
        primary: AIProvider,
        fallback: AIProvider,
        max_retries_per_provider: int = 2,
    ):
        self.providers = [primary, fallback]
        self.max_retries = max_retries_per_provider

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        last_error = None
        for provider in self.providers:
            for attempt in range(self.max_retries + 1):
                try:
                    return await provider.generate_with_retry(request, max_retries=0)
                except ProviderError as e:
                    last_error = e
                    logger.warning(
                        "Provider attempt failed",
                        provider=provider.name.value,
                        attempt=attempt + 1,
                        error_code=e.code,
                        message=e.message,
                    )
                    break
        raise ProviderError(
            provider=ProviderName.OPENROUTER,
            code="all_providers_failed",
            message=f"All providers exhausted. Last error: {last_error}",
            raw_response=last_error.raw_response if last_error else None,
        )

    async def health_check_all(self) -> dict[ProviderName, bool]:
        results = {}
        for provider in self.providers:
            try:
                results[provider.name] = await provider.health_check()
            except Exception:
                results[provider.name] = False
        return results


def create_orchestrator(
    primary_provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> AIOrchestrator:
    settings = get_settings()
    primary_name = primary_provider or settings.ai_primary_provider
    fallback_name = settings.ai_fallback_provider

    if primary_name == fallback_name:
        fallback_name = "nim" if primary_name == "openrouter" else "openrouter"

    openrouter_provider = OpenRouterProvider(
        api_key=api_key if (primary_name == "openrouter" and api_key) else settings.openrouter_api_key,
        default_model=model if (primary_name == "openrouter" and model) else settings.openrouter_default_model,
    )
    nim_provider = NIMProvider(
        api_key=api_key if (primary_name == "nim" and api_key) else settings.nim_api_key,
        default_model=model if (primary_name == "nim" and model) else settings.nim_default_model,
    )

    providers = {
        "openrouter": openrouter_provider,
        "nim": nim_provider,
    }

    primary = providers.get(primary_name)
    fallback = providers.get(fallback_name)

    if not primary:
        raise ValueError(f"Unknown primary provider: {primary_name}")
    if not fallback:
        raise ValueError(f"Unknown fallback provider: {fallback_name}")

    return AIOrchestrator(
        primary=primary,
        fallback=fallback,
        max_retries_per_provider=settings.ai_max_retries_per_provider,
    )
