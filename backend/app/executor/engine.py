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
            follow_redirects=True,
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
        headers = dict(test_case.request.headers)
        query_params = dict(test_case.request.query_params)

        auth_config = run_context.config.auth_override or run_context.config.spec_auth_config
        if auth_config and auth_config.token_env_var:
            import os
            token = os.environ.get(auth_config.token_env_var)
            if token:
                if auth_config.type == "bearer":
                    headers["Authorization"] = f"Bearer {token}"

        masked_headers = dict(headers)
        if "Authorization" in masked_headers:
            auth_val = masked_headers["Authorization"]
            if auth_val.startswith("Bearer "):
                masked_headers["Authorization"] = f"Bearer {auth_val[7:10]}***"

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                start = time.perf_counter()
                response = await self.client.request(
                    method=test_case.request.method,
                    url=url,
                    headers=headers,
                    params=query_params,
                    json=test_case.request.body if test_case.request.body else None,
                )
                duration_ms = int((time.perf_counter() - start) * 1000)

                response_body = response.read()
                body_truncated = False
                body_hash = None
                response_data = None

                if response_body:
                    body_hash = f"sha256:{hashlib.sha256(response_body).hexdigest()}"
                    if len(response_body) > self.max_response_body_bytes:
                        body_truncated = True
                        response_data = response_body[:self.max_response_body_bytes].decode("utf-8", errors="replace")
                    else:
                        response_data = response_body.decode("utf-8", errors="replace")

                assertions = evaluate_assertions(
                    test_case.expected.assertions,
                    response.status_code,
                    response.headers,
                    response_data,
                    test_case.expected.response_schema,
                    test_case.expected.status_code,
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
                        url=str(response.url),
                        headers=masked_headers,
                        body=test_case.request.body,
                    ),
                    response=ResponseReceived(
                        status_code=response.status_code,
                        headers=dict(response.headers),
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
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
            except httpx.NetworkError as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
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
            request_sent=RequestSent(method=test_case.request.method, url=url, headers=masked_headers, body=test_case.request.body),
            response=ResponseReceived(status_code=0, duration_ms=0),
            error=str(last_error),
            attempt=attempt + 1,
        )

    async def close(self):
        await self.client.aclose()
