import pytest

from app.ai.orchestrator import AIOrchestrator
from app.ai.providers.base import AIProvider, GenerationRequest, GenerationResponse, ProviderError, ProviderName


class FakeProvider(AIProvider):
    def __init__(self, name: ProviderName, failures: list[str] | None = None):
        self._provider_name = name
        self.failures = list(failures or [])
        self.calls = 0

    @property
    def name(self):
        return self._provider_name

    @property
    def default_model(self):
        return "test-model"

    @property
    def supports_json_mode(self):
        return True

    async def generate(self, request):
        self.calls += 1
        if self.failures:
            code = self.failures.pop(0)
            raise ProviderError(self.name, code, code)
        return GenerationResponse(
            content='{"test_cases": [{"title": "ok"}]}',
            provider=self.name,
            model=self.default_model,
            tokens_used=3,
            latency_ms=1,
            raw_response={},
        )

    async def health_check(self):
        return True


@pytest.mark.asyncio
async def test_empty_provider_failure_retries_then_fails_over():
    primary = FakeProvider(ProviderName.NVIDIA_NIM, ["empty_response", "empty_response", "empty_response"])
    fallback = FakeProvider(ProviderName.OPENROUTER)
    orchestrator = AIOrchestrator(primary, fallback, max_retries_per_provider=2)

    response = await orchestrator.generate(GenerationRequest(prompt="test"))

    assert response.provider == ProviderName.OPENROUTER
    assert primary.calls == 3
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_validator_failure_is_not_reported_as_success():
    primary = FakeProvider(ProviderName.NVIDIA_NIM)
    fallback = FakeProvider(ProviderName.OPENROUTER)
    orchestrator = AIOrchestrator(primary, fallback, max_retries_per_provider=0)

    response, parsed = await orchestrator.generate(
        GenerationRequest(prompt="test"), validator=lambda result: [result.content]
    )

    assert response.provider == ProviderName.NVIDIA_NIM
    assert parsed == [response.content]


@pytest.mark.asyncio
async def test_success_resets_provider_breaker_before_validation():
    primary = FakeProvider(ProviderName.NVIDIA_NIM, ["timeout"])
    fallback = FakeProvider(ProviderName.OPENROUTER)
    orchestrator = AIOrchestrator(primary, fallback, max_retries_per_provider=1)
    orchestrator._failure_threshold = 1

    response = await orchestrator.generate(GenerationRequest(prompt="test"))

    assert response.provider == ProviderName.NVIDIA_NIM
    assert orchestrator._circuits[ProviderName.NVIDIA_NIM]["failures"] == 0


@pytest.mark.asyncio
async def test_config_error_does_not_count_toward_provider_breaker():
    primary = FakeProvider(ProviderName.NVIDIA_NIM, ["config_error"])
    fallback = FakeProvider(ProviderName.OPENROUTER)
    orchestrator = AIOrchestrator(primary, fallback, max_retries_per_provider=0)

    response = await orchestrator.generate(GenerationRequest(prompt="test"))

    assert response.provider == ProviderName.OPENROUTER
    assert orchestrator._circuits[ProviderName.NVIDIA_NIM]["failures"] == 0
