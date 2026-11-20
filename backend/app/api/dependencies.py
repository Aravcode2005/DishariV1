from fastapi import Depends, Request

from app.db.repository import Repository
from app.services.documents import DocumentService
from app.services.gemini import AIProvider
from app.services.rules import JsonRulesEngine
from app.services.workflows import WorkflowOrchestrator
from app.services.scheme_loader import SchemeLoader


def get_repository(request: Request) -> Repository:
    return request.app.state.repository


def get_rules_engine(request: Request) -> JsonRulesEngine:
    return request.app.state.rules_engine


def get_ai_provider(request: Request) -> AIProvider:
    return request.app.state.ai_provider


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_scheme_loader(request: Request) -> SchemeLoader:
    return request.app.state.scheme_loader


def get_orchestrator(repository: Repository = Depends(get_repository),
                     rules: JsonRulesEngine = Depends(get_rules_engine),
                     ai: AIProvider = Depends(get_ai_provider),
                     schemes: SchemeLoader = Depends(get_scheme_loader)) -> WorkflowOrchestrator:
    return WorkflowOrchestrator(repository, rules, ai, schemes)
