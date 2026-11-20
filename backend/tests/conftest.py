from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for key in ("DATABASE_URL", "RULES_PATH", "DOCUMENT_STORAGE_DIR", "MAX_UPLOAD_BYTES", "CORS_ORIGINS",
                "AI_PROVIDER", "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_TIMEOUT_SECONDS"):
        monkeypatch.delenv(key, raising=False)

    def forbid_network(*args, **kwargs):
        raise AssertionError("Real HTTP requests are forbidden in unit tests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid_network)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(document_storage_dir=tmp_path / "uploads", max_upload_bytes=128)


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as active:
        yield active
