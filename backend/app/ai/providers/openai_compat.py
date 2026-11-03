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
        extra_body: dict | None = None,
    ) -> None:
        self._name = name
        # Provider-specific request fields, e.g. to disable hidden reasoning tokens.
        self._extra_body = extra_body or {}
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_model = default_model
        self._capabilities = capabilities or ModelCapabilities()
        self._extra_headers = extra_headers or {}
        # Local models get a longer timeout by default
        from app.config import get_settings
        self._timeout = timeout or (180.0 if self._capabilities.is_local else get_settings().ai_request_timeout)
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
        if self._extra_body:
            kwargs["extra_body"] = self._extra_body

        start = time.perf_counter()
        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._raise_provider_error(e, latency_ms)

        latency_ms = int((time.perf_counter() - start) * 1000)
        choice = response.choices[0]
        message = choice.message
        content = message.content or ""
        reasoning = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None)
        if not content and reasoning:
            content = reasoning
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "length":
            if not request.allow_truncated:
                raise ProviderError(self.name, "truncated", "Provider stopped at the output token limit")
        elif not content.strip():
            raise ProviderError(self.name, "empty_response", "Provider returned HTTP 200 with empty content")
        if "<think>" in content and finish_reason != "length":
            import re
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        if not content and finish_reason != "length":
            raise ProviderError(self.name, "empty_response", "Provider returned reasoning without a usable answer")
        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return GenerationResponse(
            content=content,
            provider=self.name,
            model=response.model or model,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else {},
            finish_reason=finish_reason,
            completion_tokens=completion_tokens,
            content_len=len(content),
            reasoning_present=bool(reasoning),
        )

    def _raise_provider_error(self, exc: Exception, latency_ms: int) -> None:
        exc_str = str(exc)
        exc_type = type(exc).__name__
        status = getattr(exc, "status_code", None)
        if status in (400, 401, 402, 403, 404) or exc_type in {"AuthenticationError", "PermissionDeniedError"}:
            raise ProviderError(provider=self.name, code="config_error", message=str(exc))
        if status == 429 or exc_type == "RateLimitError":
            raise ProviderError(provider=self.name, code="rate_limit", message=str(exc))
        if "Timeout" in exc_type or exc_type in {"APITimeoutError", "ConnectTimeout"}:
            raise ProviderError(provider=self.name, code="timeout", message=str(exc))
        if status is not None and status >= 500:
            raise ProviderError(provider=self.name, code="server_error", message=str(exc))
        if exc_type in {"BadRequestError", "UnprocessableEntityError"} and "response_format" in exc_str.lower():
            raise ProviderError(provider=self.name, code="unsupported_response_format", message=str(exc))
        raise ProviderError(provider=self.name, code="unknown_error", message=str(exc))

    async def validate_model(self) -> dict[str, object]:
        """Check provider reachability and whether its model catalog includes this model."""
        import httpx

        headers = {**self._extra_headers}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            async with httpx.AsyncClient(timeout=min(self._timeout, 15.0)) as client:
                response = await client.get(f"{self._base_url}/models", headers=headers)
            if response.status_code >= 400:
                return {
                    "ok": False,
                    "model": self._default_model,
                    "error": f"Provider model catalog returned HTTP {response.status_code}: {response.text[:300]}",
                }
            payload = response.json()
            model_ids = {item.get("id") for item in payload.get("data", []) if isinstance(item, dict)}
            if self._default_model not in model_ids:
                return {"ok": False, "model": self._default_model, "error": f"Provider model ID invalid: {self._default_model}"}
            return {"ok": True, "model": self._default_model}
        except Exception as exc:
            return {"ok": False, "model": self._default_model, "error": f"Model validation failed: {type(exc).__name__}: {exc}"}

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

# Nemotron-style reasoning models spend most of max_tokens on hidden thinking
# (~80% in testing), which truncates structured JSON output. Disable it.
NIM_NO_REASONING_BODY = {"chat_template_kwargs": {"enable_thinking": False}}
OPENROUTER_NO_REASONING_BODY = {"reasoning": {"enabled": False}}


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
        # Reasoning tokens count against max_tokens and truncate long JSON outputs.
        extra_body=OPENROUTER_NO_REASONING_BODY,
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
        extra_body=NIM_NO_REASONING_BODY,
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


def get_provider_presets() -> dict[str, dict[str, str | bool]]:
    """Expose non-secret provider defaults from the validated runtime config."""
    from app.config import get_settings

    settings = get_settings()
    return {
        "nim": {
            "name": "NVIDIA NIM",
            "default_base_url": settings.nim_base_url,
            "default_model": settings.nim_default_model,
            "requires_key": True,
        },
        "openrouter": {
            "name": "OpenRouter",
            "default_base_url": settings.openrouter_base_url,
            "default_model": settings.openrouter_default_model,
            "requires_key": True,
        },
        "ollama": {
            "name": "Ollama (Local)",
            "default_base_url": settings.local_llm_base_url,
            "default_model": settings.local_llm_model,
            "requires_key": False,
        },
    }
