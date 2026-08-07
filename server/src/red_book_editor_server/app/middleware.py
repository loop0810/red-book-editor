from __future__ import annotations

from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID")
        if (
            not request_id
            or len(request_id) > 64
            or not all(character.isalnum() or character in "-_\." for character in request_id)
        ):
            request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
