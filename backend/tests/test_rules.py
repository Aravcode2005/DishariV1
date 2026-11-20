import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR
from app.main import create_app
from app.schemas.workflows import ExampleFacts
from app.services.rules import JsonRulesEngine, RulesConfigurationError


def test_rules_version_api(client):
    response = client.get("/api/v1/rules/version")
    assert response.status_code == 200
    assert response.json() == {"version": "example-v1", "example_only": True, "rule_count": 2}


@pytest.mark.parametrize("facts,outcome", [
    ({"quantity": 1, "confirmed": True}, "passed"),
    ({"quantity": 0}, "failed"),
    ({"quantity": None, "confirmed": True}, "unknown"),
    ({"confirmed": False}, "failed"),
])
def test_deterministic_rules(facts, outcome):
    engine = JsonRulesEngine.from_file(BACKEND_DIR / "rules/rules_v1.json")
    typed = ExampleFacts(**facts)
    assert engine.evaluate(typed) == engine.evaluate(typed)
    assert engine.evaluate(typed).outcome == outcome


@pytest.mark.parametrize("change", [
    "missing_version", "not_example", "empty_rules", "duplicate_ids", "unknown_operator",
    "wrong_numeric_type", "wrong_boolean_type", "unknown_field", "invalid_comparison", "extra_key",
])
def test_invalid_rules_configuration(tmp_path, change):
    pack = json.loads((BACKEND_DIR / "rules/rules_v1.json").read_text())
    if change == "missing_version":
        del pack["version"]
    elif change == "not_example":
        pack["example_only"] = False
    elif change == "empty_rules":
        pack["rules"] = []
    elif change == "duplicate_ids":
        pack["rules"].append(deepcopy(pack["rules"][0]))
    elif change == "unknown_operator":
        pack["rules"][0]["operator"] = "eval"
    elif change == "wrong_numeric_type":
        pack["rules"][0]["value"] = "1"
    elif change == "wrong_boolean_type":
        pack["rules"][1]["value"] = 1
    elif change == "unknown_field":
        pack["rules"][0]["field"] = "real_income"
    elif change == "invalid_comparison":
        pack["rules"][1]["operator"] = "gte"
    else:
        pack["unexpected"] = "value"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(pack))
    with pytest.raises(RulesConfigurationError):
        JsonRulesEngine.from_file(path)


def test_invalid_json_and_missing_file(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{")
    with pytest.raises(RulesConfigurationError):
        JsonRulesEngine.from_file(path)
    with pytest.raises(RulesConfigurationError):
        JsonRulesEngine.from_file(tmp_path / "missing.json")


def test_invalid_rules_prevent_startup(settings, tmp_path):
    invalid = settings.model_copy(update={"rules_path": tmp_path / "missing.json"})
    with pytest.raises(RulesConfigurationError):
        with TestClient(create_app(invalid)):
            pass
