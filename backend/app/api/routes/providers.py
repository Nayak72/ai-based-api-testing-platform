"""Provider profiles API — CRUD + test + preset discovery."""

from __future__ import annotations

import structlog
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserId
from app.db.models import ProviderProfileCreate, ProviderProfileUpdate
from app.db.repositories.providers import provider_repository
from app.safety.target_guard import TargetPolicy, TargetGuard

logger = structlog.get_logger()
router = APIRouter()

_LOCAL_PROVIDER_PRESETS = {"ollama", "lmstudio", "llamacpp"}


def _validate_provider_url(base_url: str, preset: str) -> None:
    policy = TargetPolicy.LOCAL if preset in _LOCAL_PROVIDER_PRESETS else TargetPolicy.ONLINE
    decision = TargetGuard(mode=policy).check(base_url, policy)
    if not decision.allowed:
        raise HTTPException(status_code=422, detail=f"Provider URL blocked: {decision.reason}")


def _safe_profile(profile) -> dict:
    """Strip encrypted key; expose only has_key."""
    d = profile.model_dump()
    d.pop("api_key_encrypted", None)
    d["id"] = str(d.pop("_id", profile.id))
    d["user_id"] = str(d.get("user_id", ""))
    return d


@router.get("/presets")
async def list_presets():
    """Return all known provider presets with defaults."""
    from app.ai.providers.openai_compat import get_provider_presets

    return {"presets": get_provider_presets()}


@router.get("/validate")
async def validate_configured_providers():
    """Validate configured provider model IDs before a session is approved."""
    from app.ai.orchestrator import create_orchestrator

    orchestrator = create_orchestrator()
    try:
        results = {}
        for provider in orchestrator.providers:
            validate_model = getattr(provider, "validate_model", None)
            results[provider.name.value] = (
                await validate_model() if validate_model else {"ok": await provider.health_check()}
            )
        return {"providers": results, "ok": all(item.get("ok") for item in results.values())}
    finally:
        await orchestrator.close()


@router.get("/ollama/models")
async def list_ollama_models(base_url: str = Query("http://localhost:11434")):
    """List models installed in a local Ollama instance."""
    import httpx

    _validate_provider_url(base_url, "ollama")
    tags_url = base_url.rstrip("/") + "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(tags_url)
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"models": models}
    except Exception:
        raise HTTPException(status_code=502, detail="Cannot reach the local Ollama service")


@router.get("")
async def list_providers(user_id: CurrentUserId):
    profiles = await provider_repository.list_by_user(ObjectId(user_id))
    return {"providers": [_safe_profile(p) for p in profiles]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_provider(body: ProviderProfileCreate, user_id: CurrentUserId):
    _validate_provider_url(body.base_url, body.preset.value)
    from app.ai.providers.openai_compat import OpenAICompatProvider
    validator = OpenAICompatProvider(
        name=body.preset.value,
        base_url=body.base_url,
        api_key=body.api_key,
        default_model=body.model,
        capabilities=body.capabilities,
    )
    validation = await validator.validate_model()
    await validator.close()
    if not validation.get("ok"):
        raise HTTPException(status_code=422, detail=validation.get("error", "Provider model validation failed"))
    profile = await provider_repository.create(body, ObjectId(user_id))
    return _safe_profile(profile)


@router.patch("/{profile_id}")
async def update_provider(profile_id: str, body: ProviderProfileUpdate, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    existing = await provider_repository.get_by_id(obj_id, ObjectId(user_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    if body.base_url:
        _validate_provider_url(body.base_url, existing.preset.value)
    new_url = body.base_url or existing.base_url
    new_model = body.model or existing.model
    new_key = body.api_key or (provider_repository.get_decrypted_key(existing) if existing.has_key else None)
    from app.ai.providers.openai_compat import OpenAICompatProvider
    validator = OpenAICompatProvider(
        name=existing.preset.value,
        base_url=new_url,
        api_key=new_key,
        default_model=new_model,
        capabilities=body.capabilities or existing.capabilities,
    )
    validation = await validator.validate_model()
    await validator.close()
    if not validation.get("ok"):
        raise HTTPException(status_code=422, detail=validation.get("error", "Provider model validation failed"))
    profile = await provider_repository.update(obj_id, ObjectId(user_id), body)
    if not profile:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    return _safe_profile(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(profile_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    deleted = await provider_repository.delete(obj_id, ObjectId(user_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider profile not found")


@router.post("/{profile_id}/test")
async def test_provider(profile_id: str, user_id: CurrentUserId):
    """Send a tiny prompt to verify connectivity and JSON mode."""
    import time

    try:
        obj_id = ObjectId(profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID")

    profile = await provider_repository.get_by_id(obj_id, ObjectId(user_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Provider profile not found")

    api_key = provider_repository.get_decrypted_key(profile) if profile.has_key else None

    from app.ai.providers.openai_compat import OpenAICompatProvider

    provider = OpenAICompatProvider(
        name=profile.preset,
        base_url=profile.base_url,
        api_key=api_key,
        default_model=profile.model,
        capabilities=profile.capabilities,
    )

    from app.ai.providers.base import GenerationRequest

    start = time.perf_counter()
    try:
        resp = await provider.generate(
            GenerationRequest(
                prompt='Respond with exactly this JSON: {"ok": true}',
                system_prompt="Output only valid JSON.",
                max_tokens=32,
                response_format="json_object",
            )
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        import json

        try:
            data = json.loads(resp.content)
            json_mode_works = isinstance(data, dict)
        except Exception:
            json_mode_works = False
        return {"ok": True, "latency_ms": latency_ms, "json_mode_works": json_mode_works}
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {"ok": False, "latency_ms": latency_ms, "json_mode_works": False, "error": str(e)}
    finally:
        await provider.close()
