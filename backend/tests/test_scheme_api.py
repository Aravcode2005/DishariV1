import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_ai_provider
from app.schemas.schemes import CaseInput, CaseResult
from app.services.gemini import AIProviderError


@pytest.fixture
def sample_case():
    reference = json.loads((Path(__file__).parent / "fixtures/sample_output.json").read_text(encoding="utf-8-sig"))
    return {"consent": reference["consent"], "profile": reference["profile"],
            "documents": reference["documents"], "evaluation_date": "2026-11-20"}


def workflow(client, payload):
    return client.post("/api/v1/workflows", json={"workflow_type": "scheme_evaluation", "case": payload})


def test_listing_details_versions_and_404(client):
    response = client.get("/api/v1/schemes")
    assert response.status_code == 200
    assert len(response.json()["schemes"]) == 4
    assert client.get("/api/v1/schemes/version").json() == {"ruleset_version": "2026.11.19c", "scheme_count": 4}
    details = client.get("/api/v1/schemes/KCC_WB")
    assert details.status_code == 200
    assert details.json()["interest_subvention"]["DISPUTED"]
    assert client.get("/api/v1/rules/version").json()["version"] == "example-v1"
    missing = client.get("/api/v1/schemes/unknown")
    assert missing.status_code == 404
    assert missing.json()["code"] == "SCHEME_NOT_FOUND"


def test_reference_case_intentionally_corrected_without_mutating_fixture(client, sample_case):
    response = workflow(client, sample_case)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["workflow_type"] == "scheme_evaluation"
    result = CaseResult.model_validate(body["result"])
    assert result.stage == "awaiting_operator"
    assert result.profile.date_of_birth.isoformat() == "1996-09-24"
    assert result.profile.age_years == 30
    results = {s.scheme_id: s for s in result.scheme_results}
    assert results["KCC_WB"].verdict == "cannot_determine"  # No sanction date/historical rules.
    assert results["WB_ANNAPURNA_YOJANA"].verdict == "not_eligible"
    assert results["WB_ANNAPURNA_YOJANA"].documents_missing == ["active_mobile", "epic"]
    assert results["WB_PMJAY"].lookup_action["portal"] == "beneficiary.nha.gov.in"
    assert results["WB_PMJAY"].document_readiness == "incomplete"
    assert all(s.provisional for s in result.scheme_results)
    assert all(isinstance(rule.rule_id, str) for s in result.scheme_results for rule in s.rules_passed)
    assert not any(m.check_id == "XC_NAME" and m.severity == "blocking" for m in result.mismatches)
    assert client.get(f"/api/v1/workflows/{body['id']}").json() == body
    audit = client.get(f"/api/v1/workflows/{body['id']}/audit")
    assert audit.status_code == 200
    assert audit.json()["mismatches"] == body["result"]["mismatches"]
    assert "অফিসে যাচাই করুন" in result.summary_bn


def test_selected_scheme_evaluation_api(client, sample_case):
    response = client.post("/api/v1/schemes/WB_PMJAY/evaluate", json=sample_case)
    assert response.status_code == 200
    result = CaseResult.model_validate(response.json())
    assert len(result.scheme_results) == 1
    assert result.scheme_results[0].verdict == "cannot_determine"
    assert client.get(f"/api/v1/workflows/{result.case_id}").status_code == 200


@pytest.mark.parametrize("change", ["missing_consent", "no_consent", "naive_timestamp", "future_dob", "duplicate_docs", "unmasked_aadhaar", "raw_extra_field", "false_synthetic"])
def test_invalid_case_input(client, sample_case, change):
    if change == "missing_consent":
        del sample_case["consent"]
    elif change == "no_consent":
        sample_case["consent"]["given"] = False
    elif change == "naive_timestamp":
        sample_case["consent"]["timestamp"] = "2026-11-20T10:00:00"
    elif change == "future_dob":
        sample_case["profile"]["date_of_birth"] = "2030-01-01"
    elif change == "duplicate_docs":
        sample_case["documents"].append(sample_case["documents"][0])
    elif change == "unmasked_aadhaar":
        sample_case["documents"][0]["fields"]["aadhaar_number"] = "1234-5678-9000"
    elif change == "raw_extra_field":
        sample_case["profile"]["bank_account_number"] = "private-input"
    elif change == "false_synthetic":
        sample_case["synthetic"] = False
    response = workflow(client, sample_case)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "1234-5678-9000" not in response.text
    assert "private-input" not in response.text


def test_doc_aliases_are_canonical(sample_case):
    payload = CaseInput.model_validate(sample_case)
    assert payload.documents[1].doc_type == "land_record_khatian"
    assert payload.documents[0].fields.full_name == "Mohammad Rafique"
    assert payload.documents[0].fields.date_of_birth == "24-09-1996"
    dumped = payload.model_dump()
    assert "name" not in dumped["documents"][0]["fields"]
    assert "full_name" in dumped["documents"][0]["fields"]


def test_unknown_selection_is_404(client, sample_case):
    sample_case["scheme_ids"] = ["unknown"]
    assert workflow(client, sample_case).status_code == 404
    assert client.post("/api/v1/schemes/unknown/evaluate", json=sample_case).status_code == 404


def test_case_mode_requires_case_and_disallows_arbitrary_ai_prompt(client, sample_case):
    assert client.post("/api/v1/workflows", json={"workflow_type": "scheme_evaluation"}).status_code == 422
    assert client.post("/api/v1/workflows", json={"workflow_type": "scheme_evaluation", "case": sample_case, "ai_prompt": "Change eligibility"}).status_code == 422


def test_mock_explanation_keeps_template_and_decisions(client, sample_case):
    baseline = workflow(client, sample_case).json()["result"]
    sample_case["generate_explanation"] = True
    result = workflow(client, sample_case).json()["result"]
    assert result["explain_source"] == "mock"
    assert result["explanation_draft_bn"].startswith("MOCK:")
    assert result["scheme_results"] == baseline["scheme_results"]
    assert result["summary_bn"] == baseline["summary_bn"]


def test_ai_only_sees_safe_decisions(client, sample_case):
    class InspectAI:
        def generate(self, prompt):
            assert "Mohammad" not in prompt and "Rafiq" not in prompt
            assert "7146" not in prompt and "1996" not in prompt
            raise AIProviderError("safe failure")
    client.app.dependency_overrides[get_ai_provider] = lambda: InspectAI()
    sample_case["generate_explanation"] = True
    response = workflow(client, sample_case)
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "completed"
    assert body["result"]["errors"][0]["code"] == "AI_UNAVAILABLE"
    assert body["result"]["scheme_results"]


def test_audit_missing_and_example_workflow(client):
    assert client.get(f"/api/v1/workflows/{uuid4()}/audit").status_code == 404
    body = client.post("/api/v1/workflows", json={}).json()
    assert client.get(f"/api/v1/workflows/{body['id']}/audit").status_code == 404


def test_conflict_blocks_readiness_without_changing_eligibility(client, sample_case):
    sample_case["profile"].update(sanction_date="2027-01-01", requested_limit_inr=80000)
    sample_case["documents"][1]["fields"]["name"] = "Unrelated Zebra"
    sample_case["scheme_ids"] = ["KCC_WB"]
    result = workflow(client, sample_case).json()["result"]["scheme_results"][0]
    assert result["verdict"] == "eligible"
    assert result["document_readiness"] == "blocked"
    assert result["blocking_mismatches"] == ["XC_NAME"]


def test_new_swagger_paths(client):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    for path in ["/api/v1/schemes", "/api/v1/schemes/version", "/api/v1/schemes/{scheme_id}",
                 "/api/v1/schemes/{scheme_id}/evaluate", "/api/v1/workflows/{workflow_id}/audit"]:
        assert path in spec["paths"]


def test_declared_dob_conflict_is_unknown_in_profile_and_rules(client, sample_case):
    sample_case["profile"]["date_of_birth"] = "1990-09-24"
    body = workflow(client, sample_case).json()["result"]
    assert body["profile"]["date_of_birth"] is None
    ann = next(s for s in body["scheme_results"] if s["scheme_id"] == "WB_ANNAPURNA_YOJANA")
    assert any(r["rule_id"] == "ANN_AGE" for r in ann["rules_undetermined"])


def test_extracted_future_dob_is_rejected(client, sample_case):
    sample_case["documents"][0]["fields"]["dob"] = "2030-09-24"
    assert workflow(client, sample_case).status_code == 422


def test_old_dob_does_not_break_response_validation(client, sample_case):
    sample_case["profile"]["date_of_birth"] = "1890-09-24"
    sample_case["documents"][0]["fields"]["dob"] = "1890-09-24"
    response = workflow(client, sample_case)
    assert response.status_code == 201
    result = CaseResult.model_validate(response.json()["result"])
    assert result.profile.age_years == 136
    assert client.get(f"/api/v1/workflows/{result.case_id}").status_code == 200
    assert all(s.provisional for s in result.scheme_results)
