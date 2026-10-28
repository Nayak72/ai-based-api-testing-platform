"""Quick single-request test endpoint."""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUserId
from app.executor.engine import redact_headers
from app.safety.target_guard import RunMode, TargetGuard

logger = structlog.get_logger()
router = APIRouter()


class QuickTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    query_params: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    auth_type: str | None = None
    auth_token: str | None = None
    mode: RunMode = RunMode.LOCAL
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
    # Sanitize and normalize URL
    target_url = (body.url or "").strip().strip("'\"")
    if not target_url:
        return QuickTestResponse(
            status_code=0,
            headers={},
            body=None,
            body_truncated=False,
            duration_ms=0.0,
            error="Request URL is required.",
        )

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        if target_url.startswith(("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal")):
            target_url = f"http://{target_url}"
        else:
            target_url = f"https://{target_url}"

    guard = TargetGuard(mode=body.mode, owned_allowlist=[])
    allowed, reason = guard.check_url(target_url)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Target blocked: {reason}")

    # Build request headers
    req_headers: dict[str, str] = {str(k): str(v) for k, v in body.headers.items()}
    if body.auth_type == "bearer" and body.auth_token:
        req_headers["Authorization"] = f"Bearer {body.auth_token.strip()}"
    elif body.auth_type == "api_key" and body.auth_token:
        req_headers["X-API-Key"] = body.auth_token.strip()

    from app.config import get_settings

    max_body = get_settings().max_response_body_bytes
    start = time.monotonic()
    try:
        method = body.method.upper()
        send_json = body.body if (body.body is not None and method in ("POST", "PUT", "PATCH", "DELETE")) else None
        async with httpx.AsyncClient(timeout=body.timeout_seconds, follow_redirects=False) as client:
            async with client.stream(
                method=method,
                url=target_url,
                headers=req_headers,
                params=body.query_params or None,
                json=send_json,
            ) as resp:
                chunks: list[bytes] = []
                size = 0
                truncated = False
                async for chunk in resp.aiter_bytes():
                    remaining = max_body - size
                    if remaining <= 0:
                        truncated = True
                        break
                    chunks.append(chunk[:remaining])
                    size += len(chunks[-1])
                    if len(chunk) > remaining:
                        truncated = True
                        break
                raw = b"".join(chunks)
                response_headers = redact_headers(dict(resp.headers))
                response_status = resp.status_code
        duration_ms = (time.monotonic() - start) * 1000
        content_length = response_headers.get("content-length", "0")
        truncated = truncated or (content_length.isdigit() and int(content_length) > len(raw))
        try:
            import json

            parsed_body = json.loads(raw) if not truncated else raw.decode(errors="replace")
        except Exception:
            parsed_body = raw.decode(errors="replace")

        return QuickTestResponse(
            status_code=response_status,
            headers=response_headers,
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
    except Exception:
        return QuickTestResponse(
            status_code=0,
            headers={},
            body=None,
            body_truncated=False,
            duration_ms=round((time.monotonic() - start) * 1000, 2),
            error="Request could not be completed",
        )
