from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The API is run from ``backend/`` during local development, and its
# deployment-specific settings live beside that service. Environment variables
# still take precedence, so containers and hosted deployments can override it.
_env_file = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
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
    openrouter_default_model: str = ""
    openrouter_site_url: str = "http://localhost:8000"
    openrouter_site_name: str = "API Testing Platform"

    # NVIDIA NIM
    nim_api_key: str | None = None
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_default_model: str = ""

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
    local_llm_model: str = ""

    # Target Safety
    owned_host_allowlist: str | list[str] = []
    online_max_rps: float = 2.0
    online_max_concurrency: int = 3

    @field_validator("owned_host_allowlist", mode="before")
    @classmethod
    def parse_allowlist(cls, v: object) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [h.strip() for h in v.split(",") if h.strip()]
        if isinstance(v, list):
            return [str(h) for h in v]
        return []

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Production must never start with sample signing/encryption material."""
        if self.environment.casefold() != "production":
            return self

        placeholder_keys = {
            "your-super-secret-key-at-least-32-characters-long",
            "change-me",
            "secret",
            "example",
        }
        if self.debug or self.secret_key.casefold() in placeholder_keys or len(self.secret_key) < 32:
            raise ValueError("Production requires a non-placeholder SECRET_KEY of at least 32 characters")
        if not self.secrets_encryption_key:
            raise ValueError("Production requires SECRETS_ENCRYPTION_KEY")
        try:
            Fernet(self.secrets_encryption_key.encode())
        except Exception as exc:
            raise ValueError("SECRETS_ENCRYPTION_KEY must be a valid Fernet key") from exc
        if self.algorithm != "HS256":
            raise ValueError("Only JWT_ALGORITHM=HS256 is supported")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
