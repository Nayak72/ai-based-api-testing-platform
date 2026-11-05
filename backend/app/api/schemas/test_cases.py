from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AssertionSchema(BaseModel):
    type: str
    path: str
    operator: str
    value: Any | None = None


class ExpectedResponseSchema(BaseModel):
    status_code: int
    response_schema: dict | None = None
    assertions: list[AssertionSchema] = []


class RequestTemplateSchema(BaseModel):
    method: str
    path: str
    headers: dict[str, str] = {}
    query_params: dict[str, Any] = {}
    body: Any | None = None


class TestCaseMetadataSchema(BaseModel):
    __test__ = False
    owasp_category: str | None = None
    severity: str = "medium"
    generated_by: str
    generation_prompt_hash: str
    tokens_used: int
    request_hash: str


class TestCaseGenerateRequest(BaseModel):
    __test__ = False
    model_config = ConfigDict(extra="forbid")
    categories: list[str] | None = None
    prompt_version: str = "v2"
    dry_run: bool = False


class TestCaseResponse(BaseModel):
    __test__ = False
    id: str
    spec_id: str
    endpoint_id: str
    category: str
    subcategory: str
    title: str
    description: str
    request: RequestTemplateSchema
    expected: ExpectedResponseSchema
    metadata: TestCaseMetadataSchema
    created_at: datetime


class TestCaseUpdateRequest(BaseModel):
    __test__ = False
    title: str | None = None
    description: str | None = None
    request: RequestTemplateSchema | None = None
    expected: ExpectedResponseSchema | None = None


class TestCaseListResponse(BaseModel):
    __test__ = False
    test_cases: list[TestCaseResponse]
    total: int
    page: int
    page_size: int
    generation_status: str | None = None
    generation_error: str | None = None
