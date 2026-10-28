"""Catalog API routes — list and import bundled API catalog entries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserId

logger = structlog.get_logger()
router = APIRouter()

_CATALOG_PATH = Path(__file__).parent.parent.parent / "modes" / "catalog.json"
_SPECS_DIR = Path(__file__).parent.parent.parent / "modes" / "specs"


def _load_catalog() -> list[dict]:
    if not _CATALOG_PATH.exists():
        return []
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


@router.get("")
async def list_catalog():
    """Return all bundled catalog entries."""
    return {"entries": _load_catalog()}


@router.post("/{catalog_id}/import")
async def import_catalog_entry(catalog_id: str, user_id: CurrentUserId):
    """Import a catalog entry as a new spec for the current user."""
    from app.db.models import APISpecCreate
    from app.db.repositories import spec_repository

    catalog = _load_catalog()
    entry = next((e for e in catalog if e["id"] == catalog_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")

    spec_filename = entry.get("spec_path", "").split("/")[-1]
    spec_file = _SPECS_DIR / spec_filename
    if not spec_file.exists():
        raise HTTPException(status_code=404, detail=f"Bundled spec '{spec_filename}' not found")

    raw_content = spec_file.read_text(encoding="utf-8")
    spec_hash = f"sha256:{hashlib.sha256(raw_content.encode()).hexdigest()}"

    spec_create = APISpecCreate(
        name=entry["name"],
        source_type="openapi",
        source_format="json",
        raw_content=raw_content,
    )
    spec = await spec_repository.create(spec_create, user_id, spec_hash)

    # Automatically parse the spec so it is immediately ready
    try:
        from app.parsers import parse_openapi_spec

        parsed, endpoints, version, base_url = await parse_openapi_spec(raw_content)
        await spec_repository.update_parsed(
            spec.id,
            parsed,
            len(endpoints),
            version,
            base_url or entry.get("base_url"),
        )
        spec = await spec_repository.get_by_id(spec.id, user_id)
        logger.info("Catalog spec parsed successfully", catalog_id=catalog_id, endpoints=len(endpoints))
    except Exception as e:
        logger.warning("Failed to auto-parse catalog spec", catalog_id=catalog_id, error=str(e))
        await spec_repository.update_status(spec.id, "error", str(e))

    logger.info("Catalog entry imported", catalog_id=catalog_id, spec_id=str(spec.id))

    return {"spec_id": str(spec.id), "name": spec.name, "base_url": entry.get("base_url")}
