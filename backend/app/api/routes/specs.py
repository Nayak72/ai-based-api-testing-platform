import hashlib

import httpx
import structlog
from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUserId
from app.api.schemas.specs import (
    AuthConfigSchema,
    EndpointInfo,
    EndpointListResponse,
    SpecDetailResponse,
    SpecListResponse,
    SpecResponse,
    SpecUploadRequest,
)
from app.db.repositories import spec_repository
from app.parsers import extract_endpoints, parse_openapi_spec, parse_postman_collection
from app.safety.target_guard import RunMode, TargetGuard

logger = structlog.get_logger()

router = APIRouter()


def compute_spec_hash(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


@router.post("", response_model=SpecResponse, status_code=status.HTTP_201_CREATED)
async def upload_spec(
    user_id: CurrentUserId,
    file: UploadFile = File(...),
    name: str = Form(...),
    source_type: str = Form(...),
    source_format: str = Form(...),
    auth_type: str | None = Form(None),
    auth_token_env_var: str | None = Form(None),
):
    if source_type not in ("openapi", "postman"):
        raise HTTPException(status_code=400, detail="source_type must be 'openapi' or 'postman'")
    if source_format not in ("yaml", "json"):
        raise HTTPException(status_code=400, detail="source_format must be 'yaml' or 'json'")

    content = await file.read()
    raw_content = content.decode("utf-8")
    spec_hash = compute_spec_hash(raw_content)

    auth_config = None
    if auth_type:
        auth_config = {"type": auth_type, "token_env_var": auth_token_env_var}

    spec_create = SpecUploadRequest(
        name=name,
        source_type=source_type,
        source_format=source_format,
        auth_config=auth_config,
        raw_content=raw_content,
    )

    spec = await spec_repository.create(spec_create, user_id, spec_hash)

    logger.info("Spec uploaded", spec_id=str(spec.id), user_id=str(user_id))

    return SpecResponse(
        id=str(spec.id),
        name=spec.name,
        source_type=spec.source_type,
        source_format=spec.source_format,
        endpoints_count=spec.endpoints_count,
        spec_version=spec.spec_version,
        base_url=spec.base_url,
        status=spec.status,
        parse_error=spec.parse_error,
        created_at=spec.created_at,
        updated_at=spec.updated_at,
    )


@router.get("", response_model=SpecListResponse)
async def list_specs(
    user_id: CurrentUserId,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
):
    skip = (page - 1) * page_size
    specs = await spec_repository.list_by_user(user_id, skip, page_size, status_filter)
    total = await spec_repository.count_by_user(user_id, status_filter)

    return SpecListResponse(
        specs=[
            SpecResponse(
                id=str(s.id),
                name=s.name,
                source_type=s.source_type,
                source_format=s.source_format,
                endpoints_count=s.endpoints_count,
                spec_version=s.spec_version,
                base_url=s.base_url,
                status=s.status,
                parse_error=s.parse_error,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in specs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{spec_id}", response_model=SpecDetailResponse)
async def get_spec(spec_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(spec_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid spec ID")

    spec = await spec_repository.get_by_id(obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Safely convert auth_config (strips sensitive `token` field)
    auth_config_schema = None
    if spec.auth_config:
        auth_config_schema = AuthConfigSchema(
            type=spec.auth_config.type,
            token_env_var=spec.auth_config.token_env_var,
        )

    return SpecDetailResponse(
        id=str(spec.id),
        name=spec.name,
        source_type=spec.source_type,
        source_format=spec.source_format,
        endpoints_count=spec.endpoints_count,
        spec_version=spec.spec_version,
        base_url=spec.base_url,
        status=spec.status,
        parse_error=spec.parse_error,
        created_at=spec.created_at,
        updated_at=spec.updated_at,
        raw_content=spec.raw_content,
        parsed_spec=spec.parsed_spec,
        auth_config=auth_config_schema,
    )


@router.post("/{spec_id}/parse", response_model=SpecResponse)
async def parse_spec(spec_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(spec_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid spec ID")

    spec = await spec_repository.get_by_id(obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    if spec.status == "parsing":
        raise HTTPException(status_code=409, detail="Spec is already being parsed")

    await spec_repository.update_status(obj_id, "parsing")

    try:
        if spec.source_type == "openapi":
            parsed, endpoints, version, base_url = await parse_openapi_spec(spec.raw_content)
        else:
            parsed, endpoints, version, base_url = await parse_postman_collection(spec.raw_content)

        await spec_repository.update_parsed(obj_id, parsed, len(endpoints), version, base_url)
        spec = await spec_repository.get_by_id(obj_id, user_id)

        logger.info("Spec parsed successfully", spec_id=spec_id, endpoints=len(endpoints))
    except Exception as e:
        await spec_repository.update_status(obj_id, "error", str(e))
        logger.error("Spec parse failed", spec_id=spec_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Parse failed: {e!s}")

    return SpecResponse(
        id=str(spec.id),
        name=spec.name,
        source_type=spec.source_type,
        source_format=spec.source_format,
        endpoints_count=spec.endpoints_count,
        spec_version=spec.spec_version,
        base_url=spec.base_url,
        status=spec.status,
        parse_error=spec.parse_error,
        created_at=spec.created_at,
        updated_at=spec.updated_at,
    )


@router.get("/{spec_id}/endpoints", response_model=EndpointListResponse)
async def list_endpoints(spec_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(spec_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid spec ID")

    spec = await spec_repository.get_by_id(obj_id, user_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Auto-parse if raw_content is available but spec was never parsed
    if (spec.status != "ready" or not spec.parsed_spec) and spec.raw_content:
        logger.info("Auto-parsing spec on endpoints request", spec_id=spec_id)
        try:
            await spec_repository.update_status(obj_id, "parsing")
            if spec.source_type == "openapi":
                parsed, eps, version, base_url = await parse_openapi_spec(spec.raw_content)
            else:
                parsed, eps, version, base_url = await parse_postman_collection(spec.raw_content)
            await spec_repository.update_parsed(obj_id, parsed, len(eps), version, base_url)
            spec = await spec_repository.get_by_id(obj_id, user_id)
        except Exception as e:
            await spec_repository.update_status(obj_id, "error", str(e))
            logger.error("Auto-parse failed", spec_id=spec_id, error=str(e))
            raise HTTPException(status_code=400, detail=f"Spec parse failed: {e!s}")

    if spec.status != "ready" or not spec.parsed_spec:
        raise HTTPException(
            status_code=400,
            detail="Spec not parsed yet. Upload raw content first or trigger /parse.",
        )

    endpoints_data = extract_endpoints(spec.parsed_spec)
    endpoints = []
    for ep in endpoints_data:
        details = ep["operation"]
        endpoints.append(
            EndpointInfo(
                endpoint_id=ep["endpoint_id"],
                method=ep["method"],
                path=ep["path"],
                summary=details.get("summary"),
                description=details.get("description"),
                parameters=details.get("parameters", []),
                request_body=details.get("requestBody"),
                responses=details.get("responses", {}),
                security=details.get("security", spec.parsed_spec.get("security", [])),
            )
        )

    return EndpointListResponse(spec_id=spec_id, endpoints=endpoints, total=len(endpoints))


@router.delete("/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spec(spec_id: str, user_id: CurrentUserId):
    try:
        obj_id = ObjectId(spec_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid spec ID")

    deleted = await spec_repository.delete(obj_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Spec not found")

    logger.info("Spec deleted", spec_id=spec_id, user_id=str(user_id))


@router.post("/from-url", response_model=SpecResponse, status_code=status.HTTP_201_CREATED)
async def import_spec_from_url(
    body: dict,
    user_id: CurrentUserId,
):
    """Fetch an OpenAPI spec from a URL and import it."""
    url: str = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")

    mode_str = body.get("mode", "local").upper()
    try:
        mode = RunMode[mode_str]
    except KeyError:
        mode = RunMode.LOCAL

    guard = TargetGuard(mode=mode, owned_allowlist=[])
    allowed, reason = guard.check_url(url)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Target blocked: {reason}")

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "application/json, application/yaml, text/plain"})
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Request error: {e}")

    content = resp.text
    if len(content.encode("utf-8")) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Spec file too large (max 5 MB)")

    ct = resp.headers.get("content-type", "")
    if "yaml" in ct or url.endswith(".yaml") or url.endswith(".yml"):
        source_format = "yaml"
    else:
        source_format = "json"

    name = body.get("name") or url.split("/")[-1] or "imported-spec"
    spec_hash = compute_spec_hash(content)

    spec_create = SpecUploadRequest(
        name=name,
        source_type="openapi",
        source_format=source_format,
        auth_config=None,
        raw_content=content,
    )

    spec = await spec_repository.create(spec_create, user_id, spec_hash)

    # Automatically parse
    try:
        parsed, endpoints, version, base_url = await parse_openapi_spec(content)
        await spec_repository.update_parsed(spec.id, parsed, len(endpoints), version, base_url)
        spec = await spec_repository.get_by_id(spec.id, user_id)
    except Exception as e:
        await spec_repository.update_status(spec.id, "error", str(e))
        logger.warning("Failed to auto-parse imported spec", error=str(e))

    return SpecResponse(
        id=str(spec.id),
        name=spec.name,
        source_type=spec.source_type,
        source_format=spec.source_format,
        endpoints_count=spec.endpoints_count,
        spec_version=spec.spec_version,
        base_url=spec.base_url,
        status=spec.status,
        parse_error=spec.parse_error,
        created_at=spec.created_at,
        updated_at=spec.updated_at,
    )
