from typing import Protocol

from app.db.models import WorkflowRecord
from app.db.repository import Repository, StorageError
from app.schemas.workflows import WorkflowRequest, WorkflowResult
from app.services.gemini import AIProvider, AIProviderError
from app.services.rules import RulesEngine


class WorkflowExecutor(Protocol):
    def execute(self, request: WorkflowRequest) -> WorkflowRecord: ...


class WorkflowOrchestrator:
    """Synchronous MVP pipeline: validated input -> JSON rules -> optional AI -> store."""
    def __init__(self, repository: Repository, rules: RulesEngine, ai: AIProvider) -> None:
        self.repository = repository
        self.rules = rules
        self.ai = ai

    def execute(self, request: WorkflowRequest) -> WorkflowRecord:
        record = self.repository.create_workflow(request.model_dump(mode="json"))
        self.repository.transition_workflow(record.id, "pending", "running")
        result = None
        try:
            result = WorkflowResult(rules=self.rules.evaluate(request.facts))
            if request.ai_prompt is not None:
                result.ai = self.ai.generate(request.ai_prompt)
        except AIProviderError as exc:
            return self.repository.transition_workflow(
                record.id, "running", "failed",
                result=result.model_dump(mode="json") if result else None,
                error={"code": "AI_UNAVAILABLE", "message": str(exc)},
            )
        except StorageError:
            raise
        except Exception:
            self.repository.transition_workflow(record.id, "running", "failed",
                                                error={"code": "WORKFLOW_FAILED", "message": "Workflow execution failed"})
            raise
        return self.repository.transition_workflow(record.id, "running", "completed", result=result.model_dump(mode="json"))
