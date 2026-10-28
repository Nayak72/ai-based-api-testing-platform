"""NVIDIA NIM provider — thin preset wrapper over OpenAICompatProvider."""

from __future__ import annotations

from app.ai.providers.openai_compat import OpenAICompatProvider, make_nim_provider

__all__ = ["NIMProvider"]


class NIMProvider(OpenAICompatProvider):
    """Backward-compatible NIM provider; delegates to OpenAICompatProvider."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        preset = make_nim_provider(api_key=api_key, model=default_model)
        super().__init__(
            name=preset._name,
            base_url=preset._base_url,
            api_key=preset._api_key,
            default_model=preset._default_model,
            capabilities=preset._capabilities,
            extra_headers=preset._extra_headers,
        )
