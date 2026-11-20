from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from app.schemas.rules import RulePack
from app.schemas.workflows import ExampleFacts, RuleResult, RulesEvaluation


class RulesConfigurationError(Exception):
    pass


class RulesEngine(Protocol):
    def evaluate(self, facts: ExampleFacts) -> RulesEvaluation: ...


class JsonRulesEngine:
    def __init__(self, pack: RulePack) -> None:
        self.pack = pack

    @classmethod
    def from_file(cls, path: Path) -> "JsonRulesEngine":
        try:
            return cls(RulePack.model_validate_json(path.read_bytes(), strict=True))
        except (OSError, ValidationError):
            raise RulesConfigurationError("Rules file is missing or invalid; check the configured rule pack") from None

    def evaluate(self, facts: ExampleFacts) -> RulesEvaluation:
        results: list[RuleResult] = []
        for rule in self.pack.rules:
            value = getattr(facts, rule.field)
            passed = None
            if value is not None:
                passed = value >= rule.value if rule.operator == "gte" else value == rule.value
            results.append(RuleResult(rule_id=rule.id, field=rule.field, passed=passed, description=rule.description))
        outcome = "passed"
        if any(result.passed is False for result in results):
            outcome = "failed"
        elif any(result.passed is None for result in results):
            outcome = "unknown"
        return RulesEvaluation(rule_version=self.pack.version, outcome=outcome, rules=results)
