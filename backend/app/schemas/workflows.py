from datetime import datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictBool, StringConstraints, model_validator

from app.schemas.common import Schema
from app.schemas.schemes import CaseInput, CaseResult


class WorkflowState(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ExampleFacts(Schema):
    """Synthetic examples only. These are not citizen eligibility criteria."""
    quantity: Annotated[int, Field(strict=True, ge=0, le=1_000_000)] | None = None
    confirmed: StrictBool | None = None


class WorkflowRequest(Schema):
    workflow_type: Literal["example", "scheme_evaluation"] = "example"
    facts: ExampleFacts = Field(default_factory=ExampleFacts)
    case: CaseInput | None = None
    ai_prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)] | None = None


    @model_validator(mode="after")
    def valid_mode(self) -> "WorkflowRequest":
        if self.workflow_type == "scheme_evaluation":
            if self.case is None:
                raise ValueError("Scheme evaluation requires case input and consent")
            if self.ai_prompt is not None or self.facts.model_fields_set:
                raise ValueError("Use case.generate_explanation for scheme workflows; example facts are not accepted")
        elif self.case is not None:
            raise ValueError("Case input requires workflow_type=scheme_evaluation")
        return self


class RuleResult(Schema):
    rule_id: str
    field: str
    passed: bool | None
    description: str


class RulesEvaluation(Schema):
    rule_version: str
    example_only: Literal[True] = True
    outcome: Literal["passed", "failed", "unknown"]
    rules: list[RuleResult]


class AIResult(Schema):
    provider: Literal["mock", "gemini"]
    text: str


class WorkflowResult(Schema):
    rules: RulesEvaluation
    ai: AIResult | None = None


class WorkflowError(Schema):
    code: str
    message: str


class WorkflowResponse(Schema):
    id: UUID
    workflow_type: Literal["example", "scheme_evaluation"] = "example"
    state: WorkflowState
    created_at: datetime
    updated_at: datetime
    result: WorkflowResult | CaseResult | None = None
    error: WorkflowError | None = None

    @model_validator(mode="after")
    def result_mode(self) -> "WorkflowResponse":
        if isinstance(self.result, CaseResult):
            self.workflow_type = "scheme_evaluation"
        return self
