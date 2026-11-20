import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.common import ErrorResponse
from app.db.repository import StorageError
from app.services.scheme_loader import SchemeNotFoundError

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(request: Request, status: int, code: str, message: str,
                   details: list[dict] | None = None, headers: dict | None = None) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    body = ErrorResponse(code=code, message=message, request_id=request_id, details=details or [])
    return JSONResponse(status_code=status, content=body.model_dump(),
                        headers={**(headers or {}), "X-Request-ID": request_id})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SchemeNotFoundError)
    async def scheme_not_found(request: Request, exc: SchemeNotFoundError) -> JSONResponse:
        return error_response(request, 404, "SCHEME_NOT_FOUND", "Scheme not found")

    @app.exception_handler(APIError)
    async def application_error(request: Request, exc: APIError) -> JSONResponse:
        return error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not echo input values, raw request bodies, secrets or Pydantic context.
        details = [{"location": list(e["loc"]), "message": e["msg"], "type": e["type"]}
                   for e in exc.errors()]
        return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed", details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {400: "BAD_REQUEST", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "REQUEST_TOO_LARGE"}
        messages = {400: "Malformed request", 404: "Resource not found", 405: "Method not allowed",
                    413: "Request exceeds configured size limit"}
        return error_response(request, exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"),
                              messages.get(exc.status_code, "Request could not be completed"), headers=exc.headers)

    @app.exception_handler(StorageError)
    async def database_error(request: Request, exc: StorageError) -> JSONResponse:
        logger.error("database_error request_id=%s", getattr(request.state, "request_id", "unknown"))
        return error_response(request, 503, "DATABASE_UNAVAILABLE", "Database temporarily unavailable")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("internal_error request_id=%s type=%s", getattr(request.state, "request_id", "unknown"), type(exc).__name__)
        return error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred")
