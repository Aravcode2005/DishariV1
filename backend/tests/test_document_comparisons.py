import pytest

from app.services.document_audit import DocumentAudit
from app.services.rules_engine import SchemeRulesEngine
from app.services.scheme_loader import SchemeLoader


def doc(kind, **fields):
    return {"doc_type": kind, "fields": fields, "usable": True}


def audit(documents):
    return DocumentAudit(SchemeLoader()).compare(documents)


def test_reference_abbreviations_need_review_not_automatic_block():
    findings = audit([doc("aadhaar", name="Mohammad Rafique"), doc("khatian", name="Md. Rafiq"), doc("bank_passbook", name="Mohammad Rafique")])
    names = [f for f in findings if f["check_id"] == "XC_NAME"]
    assert any(f["likely_outlier"] == "land_record_khatian" for f in names)
    assert all(f["severity"] == "warning" for f in names)
    assert all(f["fix_route"]["is_inference"] for f in names)
    assert all(f["status"] == "needs_review" for f in names)


def test_clear_name_conflict_is_blocking_and_scoped():
    findings = audit([doc("aadhaar", full_name="Synthetic Alpha"), doc("bank_passbook", full_name="Synthetic Alpha"), doc("khatian", full_name="Unrelated Zebra")])
    finding = next(f for f in findings if f["check_id"] == "XC_NAME")
    assert finding["severity"] == "blocking"
    assert finding["applicable_schemes"] == ["KCC_WB"]


def test_exact_normalized_names_agree():
    assert not [f for f in audit([doc("aadhaar", name="SYNTHETIC NAME"), doc("epic", name="Synthetic Name")]) if f["check_id"] == "XC_NAME"]


def test_dob_conflict_invalidates_age():
    documents = [doc("aadhaar", dob="24-09-1996"), doc("epic", dob="1995-09-24")]
    findings = audit(documents)
    assert any(f["check_id"] == "XC_DOB" and f["severity"] == "blocking" for f in findings)
    result = SchemeRulesEngine(SchemeLoader()).evaluate({"date_of_birth": "1996-09-24"}, documents, "WB_ANNAPURNA_YOJANA", "2026-11-20")
    assert any(r["rule_id"] == "ANN_AGE" for r in result["rules_undetermined"])


@pytest.mark.parametrize("value", ["1996", "01-01-1955", "invalid"])
def test_partial_and_placeholder_dob_are_unknown(value):
    documents = [doc("aadhaar", dob=value)]
    findings = audit(documents)
    assert any(f["check_id"] == "XC_DOB" and f["status"] == "incomplete" for f in findings)
    result = SchemeRulesEngine(SchemeLoader()).evaluate({}, documents, "WB_PMJAY", "2026-11-20")
    assert any(r["rule_id"] == "PMJAY_AGE_70" for r in result["rules_undetermined"])


def test_address_variation_and_unverifiable_seeding():
    findings = audit([doc("aadhaar", address="District Alpha 700001"), doc("bank_passbook", address="District Beta 700002", bank_account_aadhaar_seeded=True)])
    assert any(f["check_id"] == "XC_ADDRESS" and f["severity"] == "warning" for f in findings)
    seeding = next(f for f in findings if f["check_id"] == "XC_AADHAAR_SEEDING")
    assert seeding["status"] == "manual_verification"
    assert "cannot be verified" in seeding["explanation"]


def test_profile_dob_conflict_does_not_override_document_evidence():
    documents = [doc("aadhaar", dob="1990-09-24")]
    result = SchemeRulesEngine(SchemeLoader()).evaluate({"date_of_birth": "1996-09-24"}, documents,
                                                       "WB_ANNAPURNA_YOJANA", "2026-11-20")
    assert any(r["rule_id"] == "ANN_AGE" for r in result["rules_undetermined"])
