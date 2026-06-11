from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class _PassThroughMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        return await call_next(request)


class RateLimitMiddleware(_PassThroughMiddleware):
    def __init__(self, app, rate: str = "100/minute") -> None:
        super().__init__(app)
        self.rate = rate


class AuditLogMiddleware(_PassThroughMiddleware):
    """Placeholder for request auditing."""


class PIIRedactionMiddleware(_PassThroughMiddleware):
    """Placeholder for log redaction."""


class PromptInjectionGuard(_PassThroughMiddleware):
    """Placeholder for prompt-injection screening."""
