from datetime import datetime

from pydantic import BaseModel, Field


class AuthConfigSchema(BaseModel):
    type: str = "bearer"
    token_env_var: str | None = None
    # Note: 'token' field intentionally omitted from API response for security

    model_config = {"from_attributes": True}


class SpecUploadRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(pattern="^(openapi|postman)$")
    source_format: str = Field(pattern="^(yaml|json)$")
    auth_config: AuthConfigSchema | None = None
    raw_content: str = ""


class SpecResponse(BaseModel):
    id: str
    name: str
    source_type: str
    source_format: str
    endpoints_count: int = 0
    spec_version: str | None = None
    base_url: str | None = None
    status: str = "parsing"
    parse_error: str | None = None
    created_at: datetime
    updated_at: datetime


class SpecDetailResponse(SpecResponse):
    raw_content: str = ""
    parsed_spec: dict | None = None
    auth_config: AuthConfigSchema | None = None


class EndpointInfo(BaseModel):
    endpoint_id: str
    method: str
    path: str
    summary: str | None = None
    description: str | None = None
    parameters: list[dict] = []
    request_body: dict | None = None
    responses: dict = {}
    security: list[dict] = []


class EndpointListResponse(BaseModel):
    spec_id: str
    endpoints: list[EndpointInfo]
    total: int


class SpecListResponse(BaseModel):
    specs: list[SpecResponse]
    total: int
    page: int
    page_size: int
