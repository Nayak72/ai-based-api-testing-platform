from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class _ObjectIdPydanticAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def validate_from_str(input_value: Any) -> ObjectId:
            if isinstance(input_value, ObjectId):
                return input_value
            if isinstance(input_value, str):
                if ObjectId.is_valid(input_value):
                    return ObjectId(input_value)
                raise ValueError("Invalid ObjectId string")
            raise ValueError("Invalid ObjectId type")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.with_info_plain_validator_function(lambda v, _: validate_from_str(v)),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())


PyObjectId = Annotated[ObjectId, _ObjectIdPydanticAnnotation]


class UserBase(BaseModel):
    email: str
    full_name: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = None


class UserInDB(UserBase):
    id: PyObjectId = Field(alias="_id")
    password_hash: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    last_login: datetime | None = None
    refresh_tokens: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class TokenBlocklist(BaseModel):
    id: PyObjectId = Field(alias="_id")
    token_hash: str
    user_id: PyObjectId
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ProviderPreset(StrEnum):
    OPENROUTER = "openrouter"
    NIM = "nim"
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    LLAMACPP = "llamacpp"


class ModelCapabilities(BaseModel):
    json_mode: bool = True
    json_schema: bool = False
    tools: bool = False
    context_window: int = 8192
    is_local: bool = False


class ProviderProfileBase(BaseModel):
    name: str
    preset: ProviderPreset
    base_url: str
    model: str
    embedding_model: str | None = None
    api_key_encrypted: str | None = None
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    is_default: bool = False


class ProviderProfileCreate(ProviderProfileBase):
    api_key: str | None = None


class ProviderProfileUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    model: str | None = None
    embedding_model: str | None = None
    api_key: str | None = None
    capabilities: ModelCapabilities | None = None
    is_default: bool | None = None


class ProviderProfileInDB(ProviderProfileBase):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    has_key: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class AuthConfig(BaseModel):
    type: str = "bearer"
    token_env_var: str | None = None
    token: str | None = None  # direct token (never stored in plaintext in DB)


class APISpecBase(BaseModel):
    name: str
    source_type: str = "openapi"
    source_format: str = "yaml"
    raw_content: str = ""
    auth_config: AuthConfig | None = None


class APISpecCreate(APISpecBase):
    pass


class APISpecInDB(APISpecBase):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    raw_content: str = ""
    parsed_spec: dict | None = None
    spec_hash: str = ""
    endpoints_count: int = 0
    spec_version: str | None = None
    base_url: str | None = None
    status: str = "parsing"
    parse_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class GenerationCache(BaseModel):
    id: PyObjectId | None = Field(alias="_id", default=None)
    spec_id: PyObjectId
    endpoint_id: str
    category: str
    prompt_version: str
    prompt_hash: str
    spec_hash: str
    test_cases: list[dict]
    tokens_used: int
    provider: str
    model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class Assertion(BaseModel):
    type: str
    path: str
    operator: str
    value: Any | None = None


class ExpectedResponse(BaseModel):
    status_code: int
    response_schema: dict | None = None
    assertions: list[Assertion] = Field(default_factory=list)


class RequestTemplate(BaseModel):
    method: str
    path: str
    headers: dict[str, str] = Field(default_factory=dict)
    query_params: dict[str, Any] = Field(default_factory=dict)
    body: Any | None = None
    raw_body: str | None = None
    content_type: str | None = None


class TestCaseMetadata(BaseModel):
    __test__ = False
    owasp_category: str | None = None
    severity: str = "medium"
    generated_by: str
    generation_prompt_hash: str
    tokens_used: int
    request_hash: str
    rag_sources: list[dict] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    extract: list[dict] = Field(default_factory=list)
    agent: str | None = None
    repairs_used: int = 0


class TestCaseBase(BaseModel):
    __test__ = False
    spec_id: PyObjectId
    endpoint_id: str
    category: str
    subcategory: str
    title: str
    description: str
    request: RequestTemplate
    expected: ExpectedResponse
    metadata: TestCaseMetadata


class TestCaseCreate(TestCaseBase):
    __test__ = False
    pass


class TestCaseInDB(TestCaseBase):
    __test__ = False
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class RunConfig(BaseModel):
    concurrency: int = 10
    timeout_seconds: float = 30.0
    retry_failed: int = 1
    categories: list[str] = Field(default_factory=lambda: ["functional", "edge", "malformed", "security"])
    base_url_override: str | None = None
    auth_override: AuthConfig | None = None
    auth_secondary: AuthConfig | None = None  # second identity for BOLA/BFLA
    spec_base_url: str | None = None
    spec_auth_config: AuthConfig | None = None
    rate_limit_rps: float | None = None
    # Phase 1 additions
    mode: Literal["local", "online"] = "local"
    intensity: Literal["safe", "standard", "aggressive"] = "standard"
    max_total_requests: int = 500
    owned_host_attestation: bool = False
    routing: dict | None = None  # LLMRouter config


class RunSummary(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    blocked: int = 0
    duration_seconds: float = 0.0


class TestRunBase(BaseModel):
    __test__ = False
    spec_id: PyObjectId
    name: str
    trigger: str = "manual"
    config: RunConfig


class TestRunCreate(TestRunBase):
    __test__ = False
    pass


class TestRunInDB(TestRunBase):
    __test__ = False
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    status: str = "pending"
    summary: RunSummary = Field(default_factory=RunSummary)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class RequestSent(BaseModel):
    method: str
    url: str
    headers: dict[str, str]
    body: Any | None = None


class ResponseReceived(BaseModel):
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any | None = None
    body_truncated: bool = False
    body_hash: str | None = None
    duration_ms: int


class AssertionResult(BaseModel):
    assertion: Assertion
    result: bool


class LLMAnalysis(BaseModel):
    risk_level: str = "low"
    summary: str
    findings: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    false_positive_likelihood: float = 0.1
    # Phase 4 additions
    verdict: str | None = None  # "real_bug", "test_bug", "spec_drift", "flaky", "environment", "ok"
    owasp_category: str | None = None
    rag_sources: list[dict] = Field(default_factory=list)


class TestResultBase(BaseModel):
    __test__ = False
    run_id: PyObjectId
    test_case_id: PyObjectId
    endpoint_id: str
    category: str
    status: str
    request_sent: RequestSent
    response: ResponseReceived
    assertions: list[AssertionResult] = Field(default_factory=list)
    error: str | None = None
    llm_analysis: LLMAnalysis | None = None
    retried: bool = False
    attempt: int = 1


class TestResultInDB(TestResultBase):
    __test__ = False
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class ReportBase(BaseModel):
    run_id: PyObjectId
    user_id: PyObjectId
    format: str = "html"


class ReportInDB(ReportBase):
    id: PyObjectId = Field(alias="_id")
    html_path: str | None = None
    pdf_path: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
    file_size_bytes: int = 0

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
