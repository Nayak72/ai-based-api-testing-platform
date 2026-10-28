"""Unified OpenAI-compatible provider. Supports Ollama, LMStudio, llamacpp, OpenRouter, NIM, OpenAI, Groq, etc."""

from __future__ import annotations

import time

import structlog

from app.ai.providers.base import (
    AIProvider,
    GenerationRequest,
    GenerationResponse,
    ProviderError,
    ProviderName,
)
from app.db.models import ModelCapabilities

logger = structlog.get_logger()


# Map preset name → ProviderName (for backward-compat)
_PRESET_TO_PROVIDER_NAME: dict[str, str] = {
    "openrouter": "openrouter",
    "nim": "nim",
    "openai_compatible": "openai_compatible",
    "ollama": "ollama",
    "lmstudio": "lmstudio",
    "llamacpp": "llamacpp",
}


class OpenAICompatProvider(AIProvider):
    """
    Single provider class for any OpenAI-compatible /chat/completions endpoint.
    Works with: OpenRouter, NVIDIA NIM, OpenAI, Groq, Together, Ollama, LMStudio, llamacpp, vLLM.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str | None,
        default_model: str,
        capabilities: ModelCapabilities | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> None:
        self._name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_model = default_model
        self._capabilities = capabilities or ModelCapabilities()
        self._extra_headers = extra_headers or {}
        # Local models get a longer timeout by default
        self._timeout = timeout or (180.0 if self._capabilities.is_local else 60.0)
        self._client = None

    @property
    def name(self) -> ProviderName:  # type: ignore[override]
        # Return an appropriate ProviderName for logging; fall back gracefully
        try:
            return ProviderName(self._name)
        except ValueError:
            return ProviderName.OPENROUTER  # fallback for unknown names

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def supports_json_mode(self) -> bool:
        return self._capabilities.json_mode

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key or "no-key",
                timeout=self._timeout,
                default_headers=self._extra_headers,
                max_retries=0,  # we handle retries ourselves
            )
        return self._client

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        client = self._get_client()
        model = request.model or self._default_model

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if self._capabilities.json_mode and request.response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        start = time.perf_counter()
        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._raise_provider_error(e, latency_ms)

        latency_ms = int((time.perf_counter() - start) * 1000)
        content = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        return GenerationResponse(
            content=content,
            provider=self.name,
            model=response.model or model,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else {},
        )

    def _raise_provider_error(self, exc: Exception, latency_ms: int) -> None:
        exc_str = str(exc).lower()
        exc_type = type(exc).__name__.lower()

        if "401" in exc_str or "403" in exc_str or "authentication" in exc_str or "unauthorized" in exc_str:
            raise ProviderError(provider=self.name, code="auth_error", message=str(exc))
        if "429" in exc_str or "rate" in exc_str:
            raise ProviderError(provider=self.name, code="rate_limit", message=str(exc))
        if "timeout" in exc_type or "timeout" in exc_str:
            raise ProviderError(provider=self.name, code="timeout", message=str(exc))
        if "500" in exc_str or "502" in exc_str or "503" in exc_str:
            raise ProviderError(provider=self.name, code="server_error", message=str(exc))
        raise ProviderError(provider=self.name, code="unknown_error", message=str(exc))

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            # For Ollama, try listing models
            if "11434" in self._base_url or "ollama" in self._name.lower():
                import httpx

                async with httpx.AsyncClient(timeout=5.0) as hc:
                    resp = await hc.get(f"{self._base_url}/models")
                    return resp.status_code == 200
            # For cloud providers, send a minimal completion
            await client.chat.completions.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


# ── Preset factories ──────────────────────────────────────────────────────────


def make_openrouter_provider(
    api_key: str | None = None,
    model: str | None = None,
    extra_headers: dict | None = None,
) -> OpenAICompatProvider:
    from app.config import get_settings

    settings = get_settings()
    return OpenAICompatProvider(
        name="openrouter",
        base_url=settings.openrouter_base_url,
        api_key=api_key or settings.openrouter_api_key,
        default_model=model or settings.openrouter_default_model,
        capabilities=ModelCapabilities(json_mode=True, tools=True, context_window=200000),
        extra_headers={
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_site_name,
            **(extra_headers or {}),
        },
    )


def make_nim_provider(
    api_key: str | None = None,
    model: str | None = None,
) -> OpenAICompatProvider:
    from app.config import get_settings

    settings = get_settings()
    return OpenAICompatProvider(
        name="nim",
        base_url=settings.nim_base_url,
        api_key=api_key or settings.nim_api_key,
        default_model=model or settings.nim_default_model,
        capabilities=ModelCapabilities(json_mode=True, tools=False, context_window=32768),
    )


def make_ollama_provider(
    base_url: str | None = None,
    model: str | None = None,
) -> OpenAICompatProvider:
    from app.config import get_settings

    settings = get_settings()
    return OpenAICompatProvider(
        name="ollama",
        base_url=base_url or settings.local_llm_base_url,
        api_key=None,
        default_model=model or settings.local_llm_model,
        capabilities=ModelCapabilities(json_mode=True, tools=False, context_window=8192, is_local=True),
        timeout=180.0,
    )


def make_lmstudio_provider(
    base_url: str | None = None,
    model: str | None = None,
) -> OpenAICompatProvider:
    from app.config import get_settings

    settings = get_settings()
    return OpenAICompatProvider(
        name="lmstudio",
        base_url=base_url or settings.local_llm_base_url,
        api_key=None,
        default_model=model or settings.local_llm_model,
        capabilities=ModelCapabilities(json_mode=True, tools=False, context_window=8192, is_local=True),
        timeout=180.0,
    )


def make_llamacpp_provider(
    base_url: str | None = None,
    model: str | None = None,
) -> OpenAICompatProvider:
    from app.config import get_settings

    settings = get_settings()
    return OpenAICompatProvider(
        name="llamacpp",
        base_url=base_url or settings.local_llm_base_url,
        api_key=None,
        default_model=model or settings.local_llm_model,
        capabilities=ModelCapabilities(json_mode=True, tools=False, context_window=8192, is_local=True),
        timeout=180.0,
    )


PROVIDER_PRESETS = {
    "openrouter": {
        "name": "OpenRouter",
        "default_base_url": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "example_models": [],
    },
    "nim": {
        "name": "NVIDIA NIM",
        "default_base_url": "https://integrate.api.nvidia.com/v1",
        "requires_key": True,
        "example_models": [],
    },
    "openai_compatible": {
        "name": "Custom OpenAI-Compatible",
        "default_base_url": "https://api.openai.com/v1",
        "requires_key": True,
        "example_models": [],
    },
    "ollama": {
        "name": "Ollama (Local)",
        "default_base_url": "http://localhost:11434/v1",
        "requires_key": False,
        "example_models": [],
    },
    "lmstudio": {
        "name": "LM Studio (Local)",
        "default_base_url": "http://localhost:1234/v1",
        "requires_key": False,
        "example_models": [],
    },
    "llamacpp": {
        "name": "llama.cpp Server (Local)",
        "default_base_url": "http://localhost:8080/v1",
        "requires_key": False,
        "example_models": [],
    },
}
