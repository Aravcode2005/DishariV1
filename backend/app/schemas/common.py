from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ValidationIssue(Schema):
    location: list[str | int]
    message: str
    type: str


class ErrorResponse(Schema):
    code: str
    message: str
    request_id: str
    details: list[ValidationIssue] = []


class HealthResponse(Schema):
    status: str = "ok"


class WelcomeResponse(Schema):
    message: str = "Welcome to the Dishari API"
