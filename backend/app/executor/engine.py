import asyncio
import hashlib
import time
from typing import TYPE_CHECKING

import httpx
import structlog

from app.db.models import (
    RequestSent,
    ResponseReceived,
    TestCaseInDB,
    TestResultBase,
)

if TYPE_CHECKING:
    from app.executor.runner import RunContext

logger = structlog.get_logger()

_SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "x-api-key", "cookie", "set-cookie"}
_IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return headers safe to persist in a result or log."""
    return {
        key: ("***" if key.casefold() in _SENSITIVE_HEADERS else value)
        for key, value in headers.items()
    }


class TokenBucket:
    def __init__(self, rate: float):
        self.rate = rate
        self.tokens = rate
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_update = time.monotonic()


class TestExecutor:
    def __init__(
        self,
        max_concurrent_requests: int = 10,
        request_timeout: float = 30.0,
        max_retries: int = 1,
        rate_limit_rps: float | None = None,
        max_response_body_bytes: int = 51200,
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.rate_limiter = TokenBucket(rate_limit_rps) if rate_limit_rps else None
        self.max_response_body_bytes = max_response_body_bytes
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(request_timeout),
            limits=httpx.Limits(max_connections=max_concurrent_requests, max_keepalive_connections=5),
            # Redirects are an SSRF boundary. They are blocked unless each hop
            # is explicitly revalidated by a future redirect-aware transport.
            follow_redirects=False,
        )

    async def execute_test_case(self, test_case: TestCaseInDB, run_context: "RunContext") -> TestResultBase:
        async with self.semaphore:
            if self.rate_limiter:
                await self.rate_limiter.acquire()
            if run_context.is_cancelled():
                return TestResultBase(
                    run_id=run_context.run_id,
                    test_case_id=test_case.id,
                    endpoint_id=test_case.endpoint_id,
                    category=test_case.category,
                    status="skipped",
                    request_sent=RequestSent(method="", url="", headers={}),
                    response=ResponseReceived(status_code=0, duration_ms=0),
                )
            return await self._execute_with_retry(test_case, run_context)

    async def _execute_with_retry(self, test_case: TestCaseInDB, run_context: "RunContext") -> TestResultBase:
        from app.executor.assertions import evaluate_assertions

        base_url = (
            run_context.config.base_url_override
            or run_context.config.spec_base_url
            or test_case.request.headers.get("x-base-url", "")
            or ""
        )
        if not base_url:
            base_url = ""

        url = f"{base_url.rstrip('/')}{test_case.request.path}"

        # TargetGuard check before sending any request
        try:
            from app.safety.target_guard import TargetGuard, TargetPolicy
            from app.config import get_settings

            policy = TargetPolicy(getattr(run_context.config, "mode", ""))
            guard = TargetGuard(mode=policy, owned_allowlist=get_settings().owned_host_allowlist)
            decision = guard.check(url, policy, guard.owned_allowlist)
            if not decision.allowed:
                return TestResultBase(
                    run_id=run_context.run_id,
                    test_case_id=test_case.id,
                    endpoint_id=test_case.endpoint_id,
                    category=test_case.category,
                    status="blocked",
                    request_sent=RequestSent(method=test_case.request.method, url=url, headers={}),
                    response=ResponseReceived(status_code=0, duration_ms=0),
                    error=f"Blocked by TargetGuard: {decision.reason}",
                )
        except Exception as guard_err:
            logger.warning("TargetGuard check failed", error=type(guard_err).__name__)
            return TestResultBase(
                run_id=run_context.run_id,
                test_case_id=test_case.id,
                endpoint_id=test_case.endpoint_id,
                category=test_case.category,
                status="blocked",
                request_sent=RequestSent(method=test_case.request.method, url=url, headers={}),
                response=ResponseReceived(status_code=0, duration_ms=0),
                error="Target validation could not be completed",
            )
        headers = dict(test_case.request.headers)
        query_params = dict(test_case.request.query_params)

        auth_config = run_context.config.auth_override or run_context.config.spec_auth_config
        if auth_config:
            token = auth_config.token
            if not token and auth_config.token_env_var:
                import os

                token = os.environ.get(auth_config.token_env_var)
            if token:
                if auth_config.type == "bearer":
                    headers["Authorization"] = f"Bearer {token}"
                elif auth_config.type == "api_key":
                    headers["X-API-Key"] = token

        masked_headers = redact_headers(headers)

        last_error = None
        retryable = test_case.request.method.upper() in _IDEMPOTENT_METHODS
        attempts = self.max_retries + 1 if retryable else 1
        for attempt in range(attempts):
            try:
                start = time.perf_counter()

                # Use raw_body if provided (for malformed JSON, wrong content-type tests)
                if test_case.request.raw_body is not None:
                    content = test_case.request.raw_body
                    if test_case.request.content_type:
                        headers["Content-Type"] = test_case.request.content_type
                    request_kwargs = {"content": content}
                else:
                    request_kwargs = {"json": test_case.request.body if test_case.request.body is not None else None}

                async with self.client.stream(
                    method=test_case.request.method,
                    url=url,
                    headers=headers,
                    params=query_params,
                    **request_kwargs,
                ) as response:
                    chunks: list[bytes] = []
                    received = 0
                    async for chunk in response.aiter_bytes():
                        remaining = self.max_response_body_bytes - received
                        if remaining <= 0:
                            break
                        chunks.append(chunk[:remaining])
                        received += len(chunks[-1])
                        if len(chunk) > remaining:
                            break
                    body_truncated = response.headers.get("content-length", "0").isdigit() and int(response.headers.get("content-length", "0")) > received
                    response_body = b"".join(chunks)
                    response_headers = redact_headers(dict(response.headers))
                    response_status = response.status_code
                    response_url = str(response.url)
                duration_ms = int((time.perf_counter() - start) * 1000)

                body_hash = None
                response_data = None

                if response_body:
                    body_hash = f"sha256:{hashlib.sha256(response_body).hexdigest()}"
                    response_data = response_body.decode("utf-8", errors="replace")

                assertions = evaluate_assertions(
                    test_case.expected.assertions,
                    response_status,
                    response_headers,
                    response_data,
                    test_case.expected.response_schema,
                    test_case.expected.status_code,
                    duration_ms,
                )

                status = "passed" if all(a.result for a in assertions) else "failed"

                return TestResultBase(
                    run_id=run_context.run_id,
                    test_case_id=test_case.id,
                    endpoint_id=test_case.endpoint_id,
                    category=test_case.category,
                    status=status,
                    request_sent=RequestSent(
                        method=test_case.request.method,
                        url=response_url,
                        headers=masked_headers,
                        body=test_case.request.raw_body
                        if test_case.request.raw_body is not None
                        else test_case.request.body,
                    ),
                    response=ResponseReceived(
                        status_code=response_status,
                        headers=response_headers,
                        body=response_data,
                        body_truncated=body_truncated,
                        body_hash=body_hash,
                        duration_ms=duration_ms,
                    ),
                    assertions=assertions,
                    attempt=attempt + 1,
                )

            except httpx.TimeoutException as e:
                last_error = e
                if attempt + 1 < attempts:
                    await asyncio.sleep(2**attempt)
                    continue
            except httpx.NetworkError as e:
                last_error = e
                if attempt + 1 < attempts:
                    await asyncio.sleep(2**attempt)
                    continue
            except Exception as e:
                last_error = e
                break

        return TestResultBase(
            run_id=run_context.run_id,
            test_case_id=test_case.id,
            endpoint_id=test_case.endpoint_id,
            category=test_case.category,
            status="error",
            request_sent=RequestSent(
                method=test_case.request.method,
                url=url,
                headers=masked_headers,
                body=test_case.request.raw_body if test_case.request.raw_body is not None else test_case.request.body,
            ),
            response=ResponseReceived(status_code=0, duration_ms=0),
            error=str(last_error),
            attempt=attempt + 1,
        )

    async def close(self):
        await self.client.aclose()
