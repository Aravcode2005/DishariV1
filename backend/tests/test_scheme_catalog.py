import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.schemas.schemes import CaseResult
from app.services.scheme_loader import DEFAULT_SCHEMES_PATH, SchemeConfigurationError, SchemeLoader, SchemeNotFoundError


def test_real_config_and_reference_json():
    loader = SchemeLoader()
    reference = json.loads((Path(__file__).parent / "fixtures/sample_output.json").read_text(encoding="utf-8-sig"))
    assert loader.version == reference["ruleset_version"] == "2026.11.19c"
    assert {s["scheme_id"] for s in loader.schemes()} == {s["scheme_id"] for s in reference["scheme_results"]}
    # This is a legacy reference with known contract errors, not executable truth.
    assert reference["scheme_results"][0]["verdict"] == "blocked_by_mismatch"
    with pytest.raises(Exception):
        CaseResult.model_validate(reference)


def test_cwd_independent_and_cached(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    loader = SchemeLoader()
    assert loader.get_scheme("KCC_WB")["scheme_id"] == "KCC_WB"
    path = tmp_path / "copy.json"
    path.write_bytes(DEFAULT_SCHEMES_PATH.read_bytes())
    loaded = SchemeLoader(path)
    path.write_text("invalid")
    assert loaded.get_scheme("KCC_WB")
    returned = loaded.get_scheme("KCC_WB")
    returned["name_en"] = "modified"
    assert loaded.get_scheme("KCC_WB")["name_en"] != "modified"


@pytest.mark.parametrize("change", ["invalid_json", "missing_version", "duplicate_scheme", "invalid_op", "bad_range", "missing_confidence", "missing_kcc_dates", "unknown_confidence"])
def test_invalid_catalog(tmp_path, change):
    data = json.loads(DEFAULT_SCHEMES_PATH.read_text(encoding="utf-8-sig"))
    if change == "missing_version":
        del data["ruleset_version"]
    elif change == "duplicate_scheme":
        data["schemes"].append(deepcopy(data["schemes"][0]))
    elif change == "invalid_op":
        data["schemes"][0]["eligibility_rules"][0]["op"] = "exec"
    elif change == "bad_range":
        rule = data["schemes"][1]["eligibility_rules"][1]
        rule["value"] = [60, 25]
    elif change == "missing_confidence":
        del data["schemes"][0]["eligibility_rules"][0]["confidence"]
    elif change == "missing_kcc_dates":
        del data["schemes"][0]["legal_basis"]["incoming"]["effective_from"]
    elif change == "unknown_confidence":
        data["schemes"][0]["eligibility_rules"][0]["confidence"] = "verified_by_ai"
    path = tmp_path / "invalid.json"
    path.write_text("{" if change == "invalid_json" else json.dumps(data))
    with pytest.raises(SchemeConfigurationError):
        SchemeLoader(path)


def test_missing_catalog_and_missing_scheme(tmp_path):
    with pytest.raises(SchemeConfigurationError):
        SchemeLoader(tmp_path / "missing.json")
    with pytest.raises(SchemeNotFoundError):
        SchemeLoader().get_scheme("missing")
