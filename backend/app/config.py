from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator(
        "rate_limit_rps",
        "openrouter_api_key",
        "nim_api_key",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    # App
    app_name: str = "API Testing Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "api_testing"

    # JWT Auth
    secret_key: str = Field(default="your-super-secret-key-at-least-32-characters-long", min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    max_refresh_tokens: int = 5

    # OpenRouter
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_site_url: str = "http://localhost:8000"
    openrouter_site_name: str = "API Testing Platform"

    # NVIDIA NIM
    nim_api_key: str | None = None
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_default_model: str = "meta/llama-3.1-70b-instruct"

    # AI Orchestrator
    ai_primary_provider: str = "openrouter"
    ai_fallback_provider: str = "nim"
    ai_max_retries_per_provider: int = 2
    ai_request_timeout: float = 60.0

    # Test Execution
    default_concurrency: int = 10
    default_request_timeout: float = 30.0
    default_max_retries: int = 1
    max_response_body_bytes: int = 51200

    # Rate Limiting (self-protection)
    rate_limit_rps: float | None = None

    # Reports
    reports_dir: str = "./data/reports"
    report_disclaimer: str = "AI-assisted testing, not a certified security audit"

    # Secrets Encryption
    secrets_encryption_key: str | None = None

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # RAG / Vector Store
    vector_dir: str = "./data/chroma"
    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Agentic Mode
    agentic_mode: bool = False
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "llama3"

    # Target Safety
    owned_host_allowlist: list[str] = []
    online_max_rps: float = 2.0
    online_max_concurrency: int = 3

    @field_validator("owned_host_allowlist", mode="before")
    @classmethod
    def parse_allowlist(cls, v: object) -> object:
        if isinstance(v, str):
            return [h.strip() for h in v.split(",") if h.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
