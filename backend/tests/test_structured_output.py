"""Tests for structured output generation."""

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.ai.providers.base import GenerationResponse, ProviderName
from app.ai.structured import generate_structured


class SimpleModel(BaseModel):
    value: int
    label: str


@pytest.mark.asyncio
async def test_json_repair_on_broken_json():
    """generate_structured should repair broken JSON and return valid Pydantic model."""
    broken_json = '{"value": 42, "label": "hello"'  # missing closing brace

    mock_response = GenerationResponse(
        content=broken_json,
        provider=ProviderName.OPENROUTER,
        model="test-model",
        tokens_used=10,
        latency_ms=100,
        raw_response={},
    )

    mock_ai = AsyncMock()
    mock_ai.generate = AsyncMock(return_value=mock_response)

    result = await generate_structured(
        ai_orchestrator=mock_ai,
        prompt="test prompt",
        system="test system",
        model_cls=SimpleModel,
    )
    assert result.value == 42
    assert result.label == "hello"


@pytest.mark.asyncio
async def test_structured_output_valid_json():
    """generate_structured should succeed immediately on valid JSON."""
    valid_json = '{"value": 100, "label": "success"}'

    mock_response = GenerationResponse(
        content=valid_json,
        provider=ProviderName.OPENROUTER,
        model="test-model",
        tokens_used=15,
        latency_ms=80,
        raw_response={},
    )

    mock_ai = AsyncMock()
    mock_ai.generate = AsyncMock(return_value=mock_response)

    result = await generate_structured(
        ai_orchestrator=mock_ai,
        prompt="test prompt",
        system="test system",
        model_cls=SimpleModel,
    )
    assert result.value == 100
    assert result.label == "success"
