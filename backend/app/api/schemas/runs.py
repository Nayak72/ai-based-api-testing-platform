from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "bearer"
    token_env_var: str | None = None


class RunConfigSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concurrency: int = Field(10, ge=1, le=100)
    timeout_seconds: float = Field(30.0, ge=1.0, le=300.0)
    retry_failed: int = Field(1, ge=0, le=5)
    categories: list[str] = Field(default_factory=lambda: ["functional", "edge", "malformed", "security"])
    base_url_override: str | None = None
    auth_override: AuthConfigSchema | None = None
    spec_base_url: str | None = None
    spec_auth_config: AuthConfigSchema | None = None
    auth_secondary: AuthConfigSchema | None = None
    rate_limit_rps: float | None = Field(default=None, gt=0)
    mode: Literal["local", "online"] = "local"
    intensity: Literal["safe", "standard", "aggressive"] = "standard"
    max_total_requests: int = Field(500, ge=1, le=10_000)
    owned_host_attestation: bool = False
    routing: dict | None = None
    auth_secret_ref: str | None = None
    test_case_ids: list[str] | None = None
    session_id: str | None = None


class RunSummarySchema(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    blocked: int = 0
    duration_seconds: float = 0.0


class ResultStorageIntegritySchema(BaseModel):
    status: Literal["valid", "inconsistent", "partially_persisted", "failed"] = "valid"
    selected_count: int = 0
    executed_count: int = 0
    persisted_count: int = 0
    summary_count: int = 0
    last_error: str | None = None
    reconciled_at: datetime | None = None


class OwaspCoverageAssessmentSchema(BaseModel):
    id: str
    name: str
    assessment: Literal["assessed", "partially_assessed", "not_assessed", "blocked_by_execution_policy"]
    applicable_endpoints: list[str] = Field(default_factory=list)
    generated_test_cases: int = 0
    executed_test_cases: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    blocked_checks: int = 0
    not_assessed_reason: str | None = None
    evidence_result_ids: list[str] = Field(default_factory=list)


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    result_integrity: ResultStorageIntegritySchema = Field(default_factory=ResultStorageIntegritySchema)
    owasp_coverage: list[OwaspCoverageAssessmentSchema] = Field(default_factory=list)
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    analysis_status: str | None = None
    analysis_total: int = 0
    analysis_completed: int = 0
    analysis_error_count: int = 0
    analysis_error: str | None = None
    analysis_started_at: datetime | None = None
    analysis_completed_at: datetime | None = None


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
