import builtins

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.db.database import create_repository
from app.db.repository import MemoryRepository, StorageError
from app.main import create_app


def test_database_optional_startup(settings, monkeypatch):
    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name == "psycopg" or name.startswith("psycopg."):
            raise AssertionError("Default startup must not import PostgreSQL")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    assert Settings.from_env().database_url is None
    with TestClient(create_app(settings)) as client:
        assert isinstance(client.app.state.repository, MemoryRepository)
        assert client.get("/health").status_code == 200


def test_missing_postgres_driver_is_clear(monkeypatch):
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "psycopg" or name.startswith("psycopg."):
            raise ImportError("test missing optional driver")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(StorageError, match="requirements-postgres"):
        create_repository("postgresql://localhost/synthetic")


def test_memory_repository_state_and_copying():
    repository = MemoryRepository()
    record = repository.create_workflow({})
    assert record.state == "pending"
    repository.transition_workflow(record.id, "pending", "running")
    repository.transition_workflow(record.id, "running", "completed", result={"example": True})
    returned = repository.get_workflow(record.id)
    returned.result["example"] = False
    assert repository.get_workflow(record.id).result["example"] is True
    with pytest.raises(ValueError):
        repository.transition_workflow(record.id, "completed", "running")
    with pytest.raises(ValueError):
        repository.transition_workflow(record.id, "pending", "running")
    assert repository.get_workflow("missing") is None
    assert MemoryRepository().get_workflow(record.id) is None


def test_memory_capacity():
    repository = MemoryRepository(max_records=1)
    repository.create_workflow({})
    with pytest.raises(StorageError):
        repository.create_workflow({})


@pytest.mark.parametrize("values", [
    {"cors_origins": ["*"]}, {"cors_origins": ["http://localhost:5173/path"]},
    {"database_url": "sqlite:///example.db"}, {"ai_provider": "gemini"},
    {"ai_provider": "gemini", "gemini_api_key": "synthetic-key"},
    {"gemini_model": "../../bad"}, {"max_upload_bytes": 0},
])
def test_invalid_settings(values):
    with pytest.raises(ValidationError):
        Settings(**values)


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "256")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "example-model")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key")
    settings = Settings.from_env()
    assert settings.database_url is None
    assert settings.max_upload_bytes == 256
    assert settings.cors_origins == ["http://localhost:5173"]
    assert "synthetic-key" not in repr(settings)
