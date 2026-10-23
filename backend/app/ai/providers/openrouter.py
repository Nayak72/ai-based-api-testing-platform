import time

import httpx
import structlog

from app.ai.providers.base import (
    AIProvider,
    GenerationRequest,
    GenerationResponse,
    ProviderError,
    ProviderName,
)
from app.config import get_settings

logger = structlog.get_logger()


class OpenRouterProvider(AIProvider):
    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        self._client: httpx.AsyncClient | None = None
        self._settings = get_settings()
        self._api_key = api_key
        self._custom_model = default_model

    @property
    def name(self) -> ProviderName:
        return ProviderName.OPENROUTER

    @property
    def default_model(self) -> str:
        return self._custom_model or self._settings.openrouter_default_model

    @property
    def supports_json_mode(self) -> bool:
        return True

    def _get_client(self) -> httpx.AsyncClient:
        key = self._api_key or self._settings.openrouter_api_key
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.openrouter_base_url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "HTTP-Referer": self._settings.openrouter_site_url,
                    "X-Title": self._settings.openrouter_site_name,
                },
                timeout=httpx.Timeout(self._settings.ai_request_timeout),
            )
        return self._client

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        key = self._api_key or self._settings.openrouter_api_key
        if not key:
            raise ProviderError(self.name, "auth_error", "OpenRouter API key not configured")

        client = self._get_client()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        target_model = request.model or self.default_model

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.response_format == "json_object" and self.supports_json_mode:
            payload["response_format"] = {"type": "json_object"}
        elif request.schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": request.schema}

        start = time.perf_counter()
        try:
            response = await client.post("/chat/completions", json=payload)
        except httpx.TimeoutException:
            raise ProviderError(self.name, "timeout", "Request timed out")
        except httpx.NetworkError as e:
            raise ProviderError(self.name, "network_error", str(e))

        latency_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code == 401:
            raise ProviderError(self.name, "auth_error", "Invalid API key")
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise ProviderError(
                self.name,
                "rate_limit",
                "Rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None,
                raw_response=response.json() if response.content else None,
            )
        if response.status_code >= 500:
            raise ProviderError(
                self.name,
                "server_error",
                f"Server error: {response.status_code}",
                raw_response=response.json() if response.content else None,
            )
        if response.status_code != 200:
            raise ProviderError(
                self.name,
                "invalid_request",
                f"Request failed: {response.status_code}",
                raw_response=response.json() if response.content else None,
            )

        data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, "invalid_response", f"Invalid response format: {e}", raw_response=data)

        return GenerationResponse(
            content=content,
            provider=self.name,
            model=data.get("model", self.default_model),
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            raw_response=data,
        )

    async def health_check(self) -> bool:
        if not self._settings.openrouter_api_key:
            return False
        try:
            client = self._get_client()
            response = await client.get("/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
