"""OpenRouter provider — thin preset wrapper over OpenAICompatProvider."""

from __future__ import annotations

from app.ai.providers.openai_compat import OpenAICompatProvider, make_openrouter_provider

__all__ = ["OpenRouterProvider"]


class OpenRouterProvider(OpenAICompatProvider):
    """Backward-compatible OpenRouter provider; delegates to OpenAICompatProvider."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        from app.config import get_settings
        resolved_model = default_model or get_settings().openrouter_default_model
        preset = make_openrouter_provider(api_key=api_key, model=resolved_model)
        super().__init__(
            name=preset._name,
            base_url=preset._base_url,
            api_key=preset._api_key,
            default_model=preset._default_model,
            capabilities=preset._capabilities,
            extra_headers=preset._extra_headers,
        )
