"""Quick single-request test endpoint."""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUserId
from app.safety.target_guard import RunMode, TargetGuard

logger = structlog.get_logger()
router = APIRouter()


class QuickTestRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: dict[str, str] = {}
    query_params: dict[str, str] = {}
    body: Any = None
    auth_type: str | None = None
    auth_token: str | None = None
    mode: str = "local"
    timeout_seconds: float = 15.0


class QuickTestResponse(BaseModel):
    status_code: int
    headers: dict[str, str]
    body: Any
    body_truncated: bool
    duration_ms: float
    error: str | None = None


@router.post("", response_model=QuickTestResponse)
async def quick_test(body: QuickTestRequest, _user_id: CurrentUserId):
    """Execute a single HTTP request and return the response."""
    mode_str = body.mode.upper()
    try:
        mode = RunMode[mode_str]
    except KeyError:
        mode = RunMode.LOCAL

    guard = TargetGuard(mode=mode, owned_allowlist=[])
    allowed, reason = guard.check_url(body.url)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Target blocked: {reason}")

    # Build request headers
    req_headers: dict[str, str] = dict(body.headers)
    if body.auth_type == "bearer" and body.auth_token:
        req_headers["Authorization"] = f"Bearer {body.auth_token}"
    elif body.auth_type == "api_key" and body.auth_token:
        req_headers["X-API-Key"] = body.auth_token

    MAX_BODY = 51200
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=body.timeout_seconds, follow_redirects=True) as client:
            resp = await client.request(
                method=body.method.upper(),
                url=body.url,
                headers=req_headers,
                params=body.query_params or None,
                json=body.body if body.body is not None else None,
            )
        duration_ms = (time.monotonic() - start) * 1000
        raw = resp.content
        truncated = len(raw) > MAX_BODY
        raw = raw[:MAX_BODY]
        try:
            parsed_body = resp.json() if not truncated else raw.decode(errors="replace")
        except Exception:
            parsed_body = raw.decode(errors="replace")

        return QuickTestResponse(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=parsed_body,
            body_truncated=truncated,
            duration_ms=round(duration_ms, 2),
        )
    except httpx.TimeoutException:
        return QuickTestResponse(
            status_code=0,
            headers={},
            body=None,
            body_truncated=False,
            duration_ms=round((time.monotonic() - start) * 1000, 2),
            error="Request timed out",
        )
    except Exception as e:
        return QuickTestResponse(
            status_code=0,
            headers={},
            body=None,
            body_truncated=False,
            duration_ms=round((time.monotonic() - start) * 1000, 2),
            error=str(e),
        )
