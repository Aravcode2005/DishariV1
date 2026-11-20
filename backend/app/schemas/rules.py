from typing import Annotated, Literal

from pydantic import Field, StrictBool, model_validator

from app.schemas.common import Schema


class RuleDefinition(Schema):
    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    field: Literal["quantity", "confirmed"]
    operator: Literal["gte", "eq"]
    value: Annotated[int, Field(strict=True, ge=0, le=1_000_000)] | StrictBool
    description: Annotated[str, Field(min_length=1, max_length=300)]

    @model_validator(mode="after")
    def compatible_comparison(self) -> "RuleDefinition":
        if self.field == "confirmed" and (self.operator != "eq" or type(self.value) is not bool):
            raise ValueError("confirmed requires eq and a boolean value")
        if self.field == "quantity" and type(self.value) is not int:
            raise ValueError("quantity requires an integer value")
        return self


class RulePack(Schema):
    version: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")]
    example_only: Literal[True]
    description: Annotated[str, Field(min_length=1, max_length=500)]
    rules: Annotated[list[RuleDefinition], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def unique_rules(self) -> "RulePack":
        if len({rule.id for rule in self.rules}) != len(self.rules):
            raise ValueError("Rule IDs must be unique")
        return self


class RulesVersionResponse(Schema):
    version: str
    example_only: Literal[True] = True
    rule_count: int
