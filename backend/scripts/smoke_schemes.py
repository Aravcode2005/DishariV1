"""Real HTTP scheme/contract verification using synthetic fixture data only."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.workflows import WorkflowResponse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-origin", default="http://localhost:5173")
    parser.add_argument("--expect-mock", action="store_true", help="Explicitly exercise the optional explanation; use only against a mock-mode server")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    checks = 0

    def call(path, expected=200, payload=None, method=None, headers=None):
        nonlocal checks
        data = json.dumps(payload).encode() if payload is not None else None
        request_headers = {"Origin": args.frontend_origin}
        if data:
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})
        request = Request(base + path, data=data, headers=request_headers, method=method)
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            assert response.status == expected, (path, response.status)
            if request_headers["Origin"] == args.frontend_origin:
                assert response.headers.get("Access-Control-Allow-Origin") == args.frontend_origin
            else:
                assert response.headers.get("Access-Control-Allow-Origin") is None
            if method != "OPTIONS":
                assert response.headers.get("X-Request-ID")
            checks += 1
            print(f"PASS {request.get_method()} {path}: HTTP {expected}")
            return body

    fixture = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/scheme_request.json").read_text(encoding="utf-8-sig"))
    call("/api/v1/workflows", method="OPTIONS", headers={
        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type"})
    assert json.loads(call("/health")) == {"status": "ok"}
    call("/health", headers={"Origin": "https://unlisted.example"})
    assert len(json.loads(call("/api/v1/schemes"))["schemes"]) == 4
    assert json.loads(call("/api/v1/schemes/version"))["ruleset_version"] == "2026.11.19c"
    assert json.loads(call("/api/v1/schemes/KCC_WB"))["legal_basis"]["incoming"]["effective_from"] == "2027-01-01"
    workflow = json.loads(call("/api/v1/workflows", 201, fixture))
    validated = WorkflowResponse.model_validate(workflow)
    assert validated.workflow_type == "scheme_evaluation"
    assert validated.state.value == "completed"
    case = workflow["result"]
    assert case["case_id"] == workflow["id"]
    assert case["ruleset_version"] == "2026.11.19c"
    assert case["stage"] == "awaiting_operator"
    assert case["profile"]["age_years"] == 30
    results = {s["scheme_id"]: s for s in case["scheme_results"]}
    for scheme in results.values():
        # This deliberately incomplete fixture cannot establish any final eligibility.
        assert scheme["verdict"] == "cannot_determine"
        assert scheme["provisional"] is True
        assert scheme["lowest_confidence_used"] == "secondary_unverified"
        for bucket, status in (("rules_passed", "passed"), ("rules_failed", "failed"), ("rules_undetermined", "undetermined")):
            for rule in scheme[bucket]:
                assert rule["status"] == status
                assert "evidence" in rule and "proved_by_document" in rule
                if rule["confidence"] == "secondary_unverified":
                    assert rule["effective_blocking"] is False
        print("RESULT", scheme["scheme_id"], scheme["verdict"], scheme["document_readiness"], scheme["lowest_confidence_used"], "provisional=true")
    assert any(r["missing_field"] == "sanction_date" for r in results["KCC_WB"]["rules_undetermined"])
    assert results["WB_PMJAY"]["lookup_action"]["portal"] == "beneficiary.nha.gov.in"
    assert not any(f["check_id"] == "XC_NAME" and f["status"] == "conflict" for f in case["mismatches"])
    assert any(f["check_id"] == "XC_AADHAAR_SEEDING" and f["status"] == "manual_verification" for f in case["mismatches"])
    assert json.loads(call("/api/v1/workflows/" + workflow["id"])) == workflow
    assert json.loads(call("/api/v1/workflows/" + workflow["id"] + "/audit"))["mismatches"] == case["mismatches"]
    result = json.loads(call("/api/v1/schemes/WB_PMJAY/evaluate", payload=fixture["case"]))
    assert result["scheme_results"][0]["verdict"] == "cannot_determine"
    assert json.loads(call("/api/v1/schemes/unknown", 404))["code"] == "SCHEME_NOT_FOUND"

    variation = deepcopy(fixture)
    variation["case"]["scheme_ids"] = ["KCC_WB"]
    variation["case"]["profile"]["sanction_date"] = "2027-01-01"  # Explicit synthetic future-version scenario.
    variation["case"]["documents"][1]["fields"]["full_name"] = "Synthetic A."
    result = json.loads(call("/api/v1/workflows", 201, variation))["result"]
    assert any(f["check_id"] == "XC_NAME" and f["status"] == "needs_review" for f in result["mismatches"])
    assert not result["scheme_results"][0]["blocking_mismatches"]
    variation["case"]["documents"][1]["fields"]["full_name"] = "Unrelated Zebra"
    result = json.loads(call("/api/v1/workflows", 201, variation))["result"]
    assert result["scheme_results"][0]["verdict"] == "eligible"
    assert result["scheme_results"][0]["document_readiness"] == "blocked"
    assert result["scheme_results"][0]["blocking_mismatches"] == ["XC_NAME"]

    old = deepcopy(fixture)
    old["case"]["profile"]["date_of_birth"] = "1890-09-24"
    old["case"]["documents"][0]["fields"]["date_of_birth"] = "1890-09-24"
    old_result = json.loads(call("/api/v1/workflows", 201, old))
    WorkflowResponse.model_validate(old_result)
    assert old_result["result"]["profile"]["age_years"] == 136

    invalid = deepcopy(fixture)
    invalid["case"]["consent"]["given"] = False
    error = json.loads(call("/api/v1/workflows", 422, invalid))
    assert error["code"] == "VALIDATION_ERROR" and error["request_id"]
    if args.expect_mock:
        explanation_request = deepcopy(fixture)
        explanation_request["case"]["generate_explanation"] = True
        explanation = json.loads(call("/api/v1/workflows", 201, explanation_request))["result"]
        assert explanation["explain_source"] == "mock"
        assert explanation["explanation_draft_bn"].startswith("MOCK:")
        assert explanation["scheme_results"] == case["scheme_results"]
        assert explanation["summary_bn"] == case["summary_bn"]
    assert b"SwaggerUIBundle" in call("/docs")
    assert "/api/v1/schemes/{scheme_id}/evaluate" in json.loads(call("/openapi.json"))["paths"]
    print(f"{checks} real HTTP scheme/contract checks passed against {base}")


if __name__ == "__main__":
    main()
