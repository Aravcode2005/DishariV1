from datetime import date

import pytest

from app.services.rules_engine import SchemeRulesEngine, age_on, evaluate_operator
from app.services.scheme_loader import SchemeLoader


@pytest.fixture
def engine():
    return SchemeRulesEngine(SchemeLoader())


def document(kind, **fields):
    return {"doc_type": kind, "fields": fields, "usable": True}


def kcc(**changes):
    return {"applicant_type": "sharecropper_bargadar", "crop_or_activity_has_notified_sof": True,
            "sanction_date": "2027-01-01", "date_of_birth": "1996-09-24", "requested_limit_inr": 50000, **changes}


def evaluate(engine, profile, docs=None, scheme="KCC_WB"):
    return engine.evaluate(profile, docs or [], scheme, "2027-01-02")


@pytest.mark.parametrize("op,actual,expected,result", [
    ("equals", False, False, True), ("equals", False, True, False),
    ("equals", 1, True, None), ("equals", None, False, None),
    ("in", "tenant_farmer", ["tenant_farmer", "fisher"], True),
    ("in", "other", ["tenant_farmer"], False), ("in", True, [1], None),
    ("between", 25, [25, 60], True), ("between", 60, [25, 60], True),
    ("between", 61, [25, 60], False), ("between", None, [25, 60], None),
    ("gte", 10, 10, True), ("gte", 9, 10, False), ("gte", True, 1, None),
    ("lte", 10000, 10000, True), ("lte", 10001, 10000, False),
    ("always_pass", None, None, True), ("gte", "10", 10, None),
])
def test_operators(op, actual, expected, result):
    assert evaluate_operator(op, actual, expected) is result


@pytest.mark.parametrize("dob,reference,age", [
    ("1996-09-24", "2026-09-23", 29), ("1996-09-24", "2026-09-24", 30),
    ("2004-02-29", "2025-02-28", 20), ("2004-02-29", "2025-03-01", 21),
    ("2030-01-01", "2026-01-01", None),
])
def test_age_boundaries(dob, reference, age):
    assert age_on(date.fromisoformat(dob), date.fromisoformat(reference)) == age


@pytest.mark.parametrize("category", ["owner_cultivator_individual", "owner_cultivator_joint", "tenant_farmer", "oral_lessee", "sharecropper_bargadar", "shg", "jlg", "animal_husbandry_farmer", "fisher", "fish_farmer", "allied_activity_farmer"])
def test_kcc_categories(engine, category):
    result = evaluate(engine, kcc(applicant_type=category), [document("land_record_khatian")])
    assert result["verdict"] == "eligible"
    assert result["provisional"] is True


def test_kcc_rejects_only_sourced_blocking_failures(engine):
    assert evaluate(engine, kcc(applicant_type="uncovered"), [document("land_record_khatian")])["verdict"] == "not_eligible"
    assert evaluate(engine, kcc(crop_or_activity_has_notified_sof=False), [document("land_record_khatian")])["verdict"] == "not_eligible"
    assert evaluate(engine, kcc(crop_or_activity_has_notified_sof=None), [document("land_record_khatian")])["verdict"] == "cannot_determine"


@pytest.mark.parametrize("kind", ["land_record_khatian", "tenancy_certificate", "pri_cultivation_certificate"])
def test_uncapped_kcc_alternatives(engine, kind):
    result = evaluate(engine, kcc(requested_limit_inr=80000), [document(kind)])
    assert result["verdict"] == "eligible"
    assert result["limit_cap_inr"] is None
    assert result["documents_missing"] == []


@pytest.mark.parametrize("amount,verdict", [(49999, "eligible"), (50000, "eligible"), (50001, "cannot_determine"), (None, "cannot_determine")])
def test_affidavit_cap(engine, amount, verdict):
    result = evaluate(engine, kcc(requested_limit_inr=amount), [document("cultivation_affidavit")])
    assert result["verdict"] == verdict
    assert result["limit_cap_inr"] == 50000
    if verdict == "cannot_determine":
        assert result["document_readiness"] == "incomplete"
        assert "cultivation_affidavit" not in result["documents_missing"]


def test_land_alternative_overrides_affidavit_cap(engine):
    result = evaluate(engine, kcc(requested_limit_inr=80000), [document("cultivation_affidavit"), document("tenancy_certificate")])
    assert result["verdict"] == "eligible"
    assert result["limit_cap_inr"] is None


@pytest.mark.parametrize("sanction", [None, "2026-11-20", "2026-12-31"])
def test_historical_kcc_is_undetermined(engine, sanction):
    result = evaluate(engine, kcc(sanction_date=sanction), [document("land_record_khatian")])
    assert result["verdict"] == "cannot_determine"
    assert not any(r["rule_id"] == "KCC_SOF_NOTIFIED" for r in result["rules_passed"])
    assert "Sanction date" in result["note"] or "historical" in result["note"]


def test_bank_policy_cannot_reject(engine):
    result = evaluate(engine, kcc(date_of_birth="1940-01-02", has_coborrower_legal_heir=False), [document("land_record_khatian")])
    assert result["verdict"] == "eligible"
    assert {r["rule_id"] for r in result["rules_failed"]} >= {"KCC_AGE_BANK", "KCC_COBORROWER_OVER_60"}
    assert all(not r["effective_blocking"] for r in result["rules_failed"])
    assert result["lowest_confidence_used"] == "secondary_unverified"


def test_always_pass_does_not_require_land_area(engine):
    result = evaluate(engine, kcc(), [document("land_record_khatian")])
    assert "KCC_NO_MIN_LANDHOLDING" in {r["rule_id"] for r in result["rules_passed"]}


def test_ann_eligibility_and_readiness_are_separate(engine):
    profile = {"gender": "F", "date_of_birth": "1990-01-02", "state_of_residence": "West Bengal",
               "is_permanent_govt_employee": False, "is_income_tax_payer": False, "monthly_individual_income_inr": 20000}
    result = evaluate(engine, profile, scheme="WB_ANNAPURNA_YOJANA")
    assert result["verdict"] == "eligible"  # Unverified advisory income rule cannot veto.
    assert result["document_readiness"] == "incomplete"
    assert set(result["documents_missing"]) == {"epic", "aadhaar", "active_mobile", "bank_passbook"}
    assert result["lowest_confidence_used"] == "secondary_unverified"


def test_missing_fields_are_unknown(engine):
    result = evaluate(engine, {}, scheme="WB_ANNAPURNA_YOJANA")
    assert result["verdict"] == "cannot_determine"
    assert not result["rules_failed"]
    assert result["rules_undetermined"][0]["missing_field"]


def test_age_uses_scheme_reference_not_supplied_age(engine):
    profile = {"date_of_birth": "2005-04-02", "age_years": 99}
    result = evaluate(engine, profile, scheme="WB_BANGLAR_YUVA_SATHI")
    age_rule = next(r for r in result["rules_failed"] if r["rule_id"] == "YS_AGE")
    assert age_rule["evidence"]["value"] == 20
    assert age_rule["evidence"]["reference_date"] == "2026-04-01"
    assert result["verdict"] == "cannot_determine"  # Every rule is unverified.


def test_yuva_exceptions_and_permanent_residence(engine):
    profile = {"date_of_birth": "1996-01-02", "highest_qualification_level": 10,
               "employment_status": "unemployed", "state_of_residence": "West Bengal",
               "receives_yuvasree": False, "receives_other_state_allowance": True,
               "other_allowance_is_scholarship": True, "is_govt_employee_or_pensioner": False}
    result = evaluate(engine, profile, [document("madhyamik_admit_card")], "WB_BANGLAR_YUVA_SATHI")
    assert any(r["rule_id"] == "YS_NOT_OTHER_ALLOWANCE" for r in result["rules_passed"])
    assert any(r["missing_field"] == "is_permanent_resident" for r in result["rules_undetermined"])
    assert "madhyamik_certificate" not in result["documents_missing"]


@pytest.mark.parametrize("dob", ["1950-01-02", "1996-09-24", None])
def test_pmjay_always_requires_lookup(engine, dob):
    result = evaluate(engine, {"date_of_birth": dob}, scheme="WB_PMJAY")
    assert result["verdict"] == "cannot_determine"
    assert result["lookup_action"]["portal"] == "beneficiary.nha.gov.in"
    assert result["provisional"] is True


def test_presence_flags_do_not_manufacture_documents(engine):
    result = evaluate(engine, kcc(has_land_record=True, documents_present=["land_record_khatian"]))
    assert result["verdict"] == "cannot_determine"
    assert result["documents_missing"]


def test_historical_kcc_does_not_quote_incoming_affidavit_cap(engine):
    result = evaluate(engine, kcc(sanction_date="2026-11-20", requested_limit_inr=80000), [document("cultivation_affidavit")])
    assert result["verdict"] == "cannot_determine"
    assert result["limit_cap_inr"] is None
    assert result["documents_missing"] == []
