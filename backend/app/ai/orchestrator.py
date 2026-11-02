import asyncio
import random
import time
from collections.abc import Callable

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
        self.primary_provider = primary.name
        self.max_retries = max_retries_per_provider
        from app.config import get_settings
        settings = get_settings()
        self._failure_threshold = settings.provider_circuit_failures
        self._cooldown = settings.provider_circuit_cooldown_seconds
        self._circuits: dict[ProviderName, dict[str, float]] = {
            provider.name: {"failures": 0, "opened_at": 0} for provider in self.providers
        }

    def _circuit_open(self, provider: AIProvider) -> bool:
        state = self._circuits[provider.name]
        if state["failures"] < self._failure_threshold:
            return False
        if time.monotonic() - state["opened_at"] >= self._cooldown:
            state["failures"] = 0
            return False
        return True

    def _record_failure(self, provider: AIProvider) -> None:
        state = self._circuits[provider.name]
        state["failures"] += 1
        if state["failures"] >= self._failure_threshold:
            state["opened_at"] = time.monotonic()

    async def generate(
        self,
        request: GenerationRequest,
        validator: Callable[[GenerationResponse], object] | None = None,
    ) -> GenerationResponse | tuple[GenerationResponse, object]:
        last_error = None
        for provider in self.providers:
            if self._circuit_open(provider):
                logger.warning("Provider circuit open", provider=provider.name.value)
                continue
            for attempt in range(self.max_retries + 1):
                try:
                    response = await provider.generate(request)
                    if validator is not None:
                        validated = validator(response)
                        return response, validated
                    self._circuits[provider.name]["failures"] = 0
                    return response
                except ProviderError as e:
                    last_error = e
                    if e.code == "unsupported_response_format" and request.response_format:
                        request.response_format = "text"
                        logger.info("Retrying without response format", provider=provider.name.value)
                        continue
                    logger.warning(
                        "Provider attempt failed",
                        provider=provider.name.value,
                        attempt=attempt + 1,
                        error_code=e.code,
                        message=e.message,
                    )
                    retryable = e.code in {
                        "rate_limit", "server_error", "timeout", "empty_response", "truncated", "invalid_output"
                    }
                    if retryable:
                        self._record_failure(provider)
                    if not retryable or attempt >= self.max_retries:
                        break
                    delay = e.retry_after or (0.5 * (2**attempt) + random.uniform(0, 0.25))
                    await asyncio.sleep(delay)
                except Exception as e:
                    last_error = ProviderError(provider.name, "invalid_output", str(e))
                    self._record_failure(provider)
                    logger.warning("Provider response validation failed", provider=provider.name.value, error=str(e))
                    if attempt >= self.max_retries:
                        break
        raise ProviderError(
            provider=self.primary_provider,
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

    async def close(self) -> None:
        await asyncio.gather(*(provider.close() for provider in self.providers), return_exceptions=True)


def create_orchestrator(
    primary_provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> AIOrchestrator:
    settings = get_settings()
    primary_name = primary_provider or settings.ai_primary_provider
    fallback_name = settings.ai_fallback_provider

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

    if not primary or not fallback:
        raise ValueError("AI provider routing must use supported configured providers")

    return AIOrchestrator(
        primary=primary,
        fallback=fallback,
        max_retries_per_provider=settings.ai_max_retries_per_provider,
    )
