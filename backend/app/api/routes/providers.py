"""Provider profiles API — CRUD + test + preset discovery."""

from __future__ import annotations

import structlog
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserId
from app.db.models import ProviderProfileCreate, ProviderProfileUpdate
from app.db.repositories.providers import provider_repository

logger = structlog.get_logger()
router = APIRouter()


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
    from app.ai.providers.openai_compat import PROVIDER_PRESETS

    return {"presets": PROVIDER_PRESETS}


@router.get("/ollama/models")
async def list_ollama_models(base_url: str = Query("http://localhost:11434")):
    """List models installed in a local Ollama instance."""
    import httpx

    tags_url = base_url.rstrip("/") + "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(tags_url)
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach Ollama at {base_url}: {e}")


@router.get("")
async def list_providers(user_id: CurrentUserId):
    profiles = await provider_repository.list_by_user(ObjectId(user_id))
    return {"providers": [_safe_profile(p) for p in profiles]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_provider(body: ProviderProfileCreate, user_id: CurrentUserId):
    profile = await provider_repository.create(body, ObjectId(user_id))
    return _safe_profile(profile)


@router.patch("/{profile_id}")
async def update_provider(profile_id: str, body: ProviderProfileUpdate, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(profile_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile ID")
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
