from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import get_document_service, get_orchestrator, get_repository, get_rules_engine
from app.core.errors import APIError
from app.db.repository import Repository
from app.schemas.common import HealthResponse, WelcomeResponse
from app.schemas.documents import DocumentResponse
from app.schemas.rules import RulesVersionResponse
from app.schemas.workflows import WorkflowRequest, WorkflowResponse
from app.services.documents import DocumentService
from app.services.rules import JsonRulesEngine
from app.services.workflows import WorkflowOrchestrator

router = APIRouter()


@router.get("/", response_model=WelcomeResponse, tags=["system"])
def welcome() -> WelcomeResponse:
    return WelcomeResponse()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness endpoint; preserves the original response."""
    return HealthResponse()


@router.post("/api/v1/workflows", response_model=WorkflowResponse, status_code=201, tags=["workflows"])
def create_workflow(payload: WorkflowRequest, orchestrator: Annotated[WorkflowOrchestrator, Depends(get_orchestrator)]) -> WorkflowResponse:
    """Run the example pipeline inline. 201 records creation; inspect state for AI failure."""
    return WorkflowResponse.model_validate(orchestrator.execute(payload))


@router.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["workflows"])
def get_workflow(workflow_id: UUID, repository: Annotated[Repository, Depends(get_repository)]) -> WorkflowResponse:
    record = repository.get_workflow(str(workflow_id))
    if record is None:
        raise APIError(404, "WORKFLOW_NOT_FOUND", "Workflow not found")
    return WorkflowResponse.model_validate(record)


@router.post("/api/v1/documents", response_model=DocumentResponse, status_code=201, tags=["documents"])
def upload_document(
    file: Annotated[UploadFile, File(description="Synthetic test data only. PDF, PNG or JPEG; default limit 10 MiB.")],
    synthetic: Annotated[Literal["true"], Form(description="Required declaration: synthetic=true. Never submit sensitive documents.")],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    """Store a synthetic file temporarily and record an audit event. No document processing."""
    try:
        return DocumentResponse.model_validate(service.store(file))
    finally:
        file.file.close()


@router.get("/api/v1/rules/version", response_model=RulesVersionResponse, tags=["rules"])
def rules_version(engine: Annotated[JsonRulesEngine, Depends(get_rules_engine)]) -> RulesVersionResponse:
    return RulesVersionResponse(version=engine.pack.version, rule_count=len(engine.pack.rules))
