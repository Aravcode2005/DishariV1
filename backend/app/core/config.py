"""Explicit environment configuration; .env files are never loaded implicitly."""
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    database_url: SecretStr | None = None
    rules_path: Path = BACKEND_DIR / "rules" / "rules_v1.json"
    document_storage_dir: Path | None = None
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    cors_origins: list[str] = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ]
    ai_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = ""
    gemini_timeout_seconds: float = Field(default=20, gt=0, le=120)

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value().strip():
            return None
        if urlsplit(value.get_secret_value()).scheme not in {"postgresql", "postgres"}:
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or "*" in origin or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
            _ = parsed.port  # Validate malformed ports as well.
        return origins

    @field_validator("gemini_model")
    @classmethod
    def safe_model_name(cls, model: str) -> str:
        if model and not re.fullmatch(r"[A-Za-z0-9._-]+", model):
            raise ValueError("GEMINI_MODEL must be a model ID, not a URL or path")
        return model

    @model_validator(mode="after")
    def online_configuration(self) -> "Settings":
        if self.ai_provider == "gemini" and (
            not self.gemini_api_key or not self.gemini_api_key.get_secret_value().strip()
            or not self.gemini_model
        ):
            raise ValueError("Gemini mode requires GEMINI_API_KEY and GEMINI_MODEL")
        return self

    @property
    def max_request_bytes(self) -> int:
        return self.max_upload_bytes + 64 * 1024  # Multipart headers/fields allowance.

    @classmethod
    def from_env(cls) -> "Settings":
        mapping = {
            "DATABASE_URL": "database_url", "RULES_PATH": "rules_path", "DOCUMENT_STORAGE_DIR": "document_storage_dir",
            "MAX_UPLOAD_BYTES": "max_upload_bytes", "AI_PROVIDER": "ai_provider",
            "GEMINI_API_KEY": "gemini_api_key", "GEMINI_MODEL": "gemini_model",
            "GEMINI_TIMEOUT_SECONDS": "gemini_timeout_seconds",
        }
        values = {field: os.environ[key] for key, field in mapping.items() if key in os.environ}
        if "CORS_ORIGINS" in os.environ:
            values["cors_origins"] = [s.strip() for s in os.environ["CORS_ORIGINS"].split(",") if s.strip()]
        return cls.model_validate(values)
