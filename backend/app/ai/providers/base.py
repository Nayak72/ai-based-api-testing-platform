from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

import structlog

logger = structlog.get_logger()


class ProviderName(StrEnum):
    OPENROUTER = "openrouter"
    NVIDIA_NIM = "nim"


@dataclass
class GenerationRequest:
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096
    response_format: str = "json_object"
    schema: dict | None = None
    model: str | None = None


@dataclass
class GenerationResponse:
    content: str
    provider: ProviderName
    model: str
    tokens_used: int
    latency_ms: int
    raw_response: dict


class ProviderError(Exception):
    def __init__(
        self,
        provider: ProviderName,
        code: str,
        message: str,
        retry_after: int | None = None,
        raw_response: dict | None = None,
    ):
        self.provider = provider
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.raw_response = raw_response
        super().__init__(f"{provider.value}: {code} - {message}")


class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> ProviderName: ...

    @property
    @abstractmethod
    def default_model(self) -> str: ...

    @property
    @abstractmethod
    def supports_json_mode(self) -> bool: ...

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    async def close(self) -> None:
        """Close any open connections. Override in subclasses if needed."""
        pass

    async def generate_with_retry(
        self,
        request: GenerationRequest,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> GenerationResponse:
        import asyncio
        import random

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return await self.generate(request)
            except ProviderError as e:
                last_error = e
                if e.code in ("rate_limit", "server_error", "timeout"):
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                        if e.retry_after:
                            delay = max(delay, e.retry_after)
                        logger.warning(
                            "Provider error, retrying",
                            provider=self.name.value,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=e.message,
                        )
                        await asyncio.sleep(delay)
                        continue
                elif e.code == "auth_error":
                    break
                else:
                    raise
        raise ProviderError(
            provider=self.name,
            code="max_retries_exceeded",
            message=f"Max retries exceeded. Last error: {last_error}",
            raw_response=last_error.raw_response if last_error else None,
        )
