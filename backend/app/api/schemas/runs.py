from datetime import datetime

from pydantic import BaseModel, Field


class AuthConfigSchema(BaseModel):
    type: str = "bearer"
    token_env_var: str | None = None


class RunConfigSchema(BaseModel):
    concurrency: int = Field(10, ge=1, le=100)
    timeout_seconds: float = Field(30.0, ge=1.0, le=300.0)
    retry_failed: int = Field(1, ge=0, le=5)
    categories: list[str] = ["functional", "edge", "malformed", "security"]
    base_url_override: str | None = None
    auth_override: AuthConfigSchema | None = None


class RunSummarySchema(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0


class RunCreateRequest(BaseModel):
    spec_id: str
    name: str = Field(min_length=1, max_length=200)
    config: RunConfigSchema | None = None


class RunResponse(BaseModel):
    id: str
    spec_id: str
    user_id: str
    name: str
    trigger: str
    status: str
    config: RunConfigSchema
    summary: RunSummarySchema
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class RunListResponse(BaseModel):
    runs: list[RunResponse]
    total: int
    page: int
    page_size: int


class ResultResponse(BaseModel):
    id: str
    run_id: str
    test_case_id: str
    endpoint_id: str
    category: str
    status: str
    request_sent: dict
    response: dict
    assertions: list[dict]
    error: str | None
    llm_analysis: dict | None
    retried: bool
    attempt: int
    created_at: datetime


class ResultListResponse(BaseModel):
    results: list[ResultResponse]
    total: int
    page: int
    page_size: int
