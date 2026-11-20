from uuid import uuid4

import pytest

from app.api.dependencies import get_ai_provider
from app.services.gemini import AIProviderError


@pytest.mark.parametrize("facts,outcome", [
    ({"quantity": 2, "confirmed": True}, "passed"),
    ({"quantity": 0, "confirmed": True}, "failed"),
    ({"quantity": 2, "confirmed": False}, "failed"),
    ({}, "unknown"),
])
def test_workflow_create_and_retrieve(client, facts, outcome):
    response = client.post("/api/v1/workflows", json={"facts": facts})
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "completed"
    assert body["result"]["rules"]["outcome"] == outcome
    assert body["result"]["rules"]["rule_version"] == "example-v1"
    assert body["result"]["rules"]["example_only"] is True
    assert body["result"]["ai"] is None
    retrieved = client.get(f"/api/v1/workflows/{body['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == body


def test_mock_gemini_workflow(client):
    body = client.post("/api/v1/workflows", json={"facts": {"quantity": 1, "confirmed": True}, "ai_prompt": "Synthetic example"}).json()
    assert body["state"] == "completed"
    assert body["result"]["ai"]["provider"] == "mock"
    assert body["result"]["ai"]["text"].startswith("MOCK:")
    assert body["result"]["rules"]["outcome"] == "passed"


def test_ai_failure_is_persisted_without_changing_rules(client):
    class FailingAI:
        def generate(self, prompt):
            raise AIProviderError("AI provider timed out")

    client.app.dependency_overrides[get_ai_provider] = lambda: FailingAI()
    response = client.post("/api/v1/workflows", json={"facts": {"quantity": 1, "confirmed": True}, "ai_prompt": "Synthetic"})
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "failed"
    assert body["error"]["code"] == "AI_UNAVAILABLE"
    assert body["result"]["rules"]["outcome"] == "passed"
    assert client.get(f"/api/v1/workflows/{body['id']}").json() == body


@pytest.mark.parametrize("payload", [
    {"facts": {"quantity": -1}}, {"facts": {"quantity": True}},
    {"facts": {"quantity": "1"}}, {"facts": {"confirmed": "true"}},
    {"workflow_type": "real_eligibility"}, {"facts": {"income": 1}},
    {"ai_prompt": "  "}, {"ai_prompt": "x" * 2001}, {"secret": "do-not-echo"},
])
def test_request_validation(client, payload):
    response = client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]
    assert body["request_id"] == response.headers["x-request-id"]
    assert "do-not-echo" not in response.text
    assert "input" not in body["details"][0]


def test_malformed_json(client):
    response = client.post("/api/v1/workflows", content=b'{"facts":', headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_missing_workflow(client):
    response = client.get(f"/api/v1/workflows/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "WORKFLOW_NOT_FOUND"


def test_invalid_workflow_id(client):
    assert client.get("/api/v1/workflows/not-a-uuid").status_code == 422


def test_unexpected_error_is_sanitized_and_workflow_fails(settings, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app

    def fail(facts):
        raise RuntimeError("private-internal-details")

    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        monkeypatch.setattr(client.app.state.rules_engine, "evaluate", fail)
        response = client.post("/api/v1/workflows", json={})
        assert response.status_code == 500
        assert response.json()["code"] == "INTERNAL_ERROR"
        assert "private-internal-details" not in response.text
        assert response.headers["x-request-id"] == response.json()["request_id"]
        record = next(iter(client.app.state.repository._workflows.values()))
        assert record.state == "failed"
