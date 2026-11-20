from uuid import uuid4

from fastapi import Request
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response


class GatewayMiddleware:
    """Assign opaque request IDs and bound bodies, including chunked uploads."""
    def __init__(self, app: ASGIApp, max_request_bytes: int) -> None:
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        request = Request(scope)
        length = request.headers.get("content-length")
        if length is not None:
            try:
                size = int(length)
                if size < 0:
                    raise ValueError
            except ValueError:
                await error_response(request, 400, "BAD_REQUEST", "Invalid Content-Length")(scope, receive, send)
                return
            if size > self.max_request_bytes:
                await error_response(request, 413, "REQUEST_TOO_LARGE", "Request exceeds configured size limit")(scope, receive, send)
                return
        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_request_bytes:
                    raise HTTPException(status_code=413)
            return message

        async def identified_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = list(message.get("headers", []))
                if not any(key.lower() == b"x-request-id" for key, _ in headers):
                    headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, limited_receive, identified_send)
        except Exception as exc:
            if response_started:
                raise  # A response already sent cannot be replaced safely.
            # Handle before returning through the outer CORS middleware. Otherwise
            # Starlette's outermost server-error handler bypasses CORS on HTTP 500.
            handler = request.app.exception_handlers.get(Exception)
            if handler is None:
                raise
            response = await handler(request, exc)
            await response(scope, limited_receive, identified_send)
