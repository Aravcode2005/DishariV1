from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_orchestrator, get_repository, get_scheme_loader
from app.core.errors import APIError
from app.db.repository import Repository
from app.schemas.schemes import CaseAuditResponse, CaseInput, CaseResult, SchemeDefinition, SchemesResponse, SchemeSummary, SchemeVersionResponse
from app.schemas.workflows import WorkflowRequest
from app.services.scheme_loader import SchemeLoader
from app.services.workflows import WorkflowOrchestrator

router = APIRouter(tags=["schemes"])


@router.get("/api/v1/schemes", response_model=SchemesResponse)
def list_schemes(loader: Annotated[SchemeLoader, Depends(get_scheme_loader)]) -> SchemesResponse:
    return SchemesResponse(ruleset_version=loader.version,
        schemes=[SchemeSummary.model_validate({k: s[k] for k in SchemeSummary.model_fields}) for s in loader.schemes()])


@router.get("/api/v1/schemes/version", response_model=SchemeVersionResponse)
def version(loader: Annotated[SchemeLoader, Depends(get_scheme_loader)]) -> SchemeVersionResponse:
    return SchemeVersionResponse(ruleset_version=loader.version, scheme_count=len(loader.schemes()))


@router.get("/api/v1/schemes/{scheme_id}", response_model=SchemeDefinition)
def scheme_details(scheme_id: str, loader: Annotated[SchemeLoader, Depends(get_scheme_loader)]) -> SchemeDefinition:
    return SchemeDefinition.model_validate(loader.get_scheme(scheme_id))


@router.post("/api/v1/schemes/{scheme_id}/evaluate", response_model=CaseResult)
def evaluate_scheme(scheme_id: str, payload: CaseInput,
                    loader: Annotated[SchemeLoader, Depends(get_scheme_loader)],
                    orchestrator: Annotated[WorkflowOrchestrator, Depends(get_orchestrator)]) -> CaseResult:
    loader.get_scheme(scheme_id)
    selected = payload.model_copy(update={"scheme_ids": [scheme_id]})
    record = orchestrator.execute(WorkflowRequest(workflow_type="scheme_evaluation", case=selected))
    return CaseResult.model_validate(record.result)


@router.get("/api/v1/workflows/{workflow_id}/audit", response_model=CaseAuditResponse, tags=["documents"])
def get_audit(workflow_id: UUID, repository: Annotated[Repository, Depends(get_repository)]) -> CaseAuditResponse:
    record = repository.get_workflow(str(workflow_id))
    if record is None:
        raise APIError(404, "WORKFLOW_NOT_FOUND", "Workflow not found")
    if not record.result or "case_id" not in record.result:
        raise APIError(404, "CASE_AUDIT_NOT_FOUND", "This workflow has no scheme document audit")
    result = CaseResult.model_validate(record.result)
    return CaseAuditResponse(case_id=result.case_id, mismatches=result.mismatches)
