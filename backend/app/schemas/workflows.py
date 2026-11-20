from datetime import datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictBool, StringConstraints

from app.schemas.common import Schema


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
    workflow_type: Literal["example"] = "example"
    facts: ExampleFacts = Field(default_factory=ExampleFacts)
    ai_prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)] | None = None


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
    workflow_type: Literal["example"] = "example"
    state: WorkflowState
    created_at: datetime
    updated_at: datetime
    result: WorkflowResult | None = None
    error: WorkflowError | None = None
