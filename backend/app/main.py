"""FastAPI gateway. Local command stays: python -m uvicorn app.main:app --reload."""
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.schemes import router as schemes_router
from app.core.config import Settings
from app.core.errors import register_exception_handlers
from app.core.middleware import GatewayMiddleware
from app.db.database import create_repository
from app.db.repository import Repository
from app.schemas.common import ErrorResponse
from app.services.documents import DocumentService
from app.services.gemini import create_ai_provider
from app.services.rules import JsonRulesEngine
from app.services.scheme_loader import SchemeLoader


def create_app(settings: Settings | None = None, repository: Repository | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.scheme_loader = SchemeLoader()
        app.state.rules_engine = JsonRulesEngine.from_file(settings.rules_path)
        app.state.repository = repository if repository is not None else create_repository(
            settings.database_url.get_secret_value() if settings.database_url else None
        )
        app.state.repository.initialize()
        app.state.ai_provider = create_ai_provider(settings)
        if settings.document_storage_dir is not None:
            settings.document_storage_dir.mkdir(parents=True, exist_ok=True)
        # A private per-process directory is removed on graceful shutdown.
        with TemporaryDirectory(prefix="dishari-synthetic-", dir=settings.document_storage_dir) as directory:
            app.state.document_service = DocumentService(app.state.repository, Path(directory), settings.max_upload_bytes)
            yield

    app = FastAPI(
        title="Dishari API", version="0.1.0",
        description="Hackathon MVP boilerplate. Example rules and synthetic documents only.",
        lifespan=lifespan,
        responses={status: {"model": ErrorResponse} for status in (400, 404, 405, 413, 415, 422, 500, 503)},
    )
    app.state.settings = settings
    register_exception_handlers(app)
    app.add_middleware(GatewayMiddleware, max_request_bytes=settings.max_request_bytes)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Request-ID"],
    )
    app.include_router(router)
    app.include_router(schemes_router)
    return app


app = create_app()
