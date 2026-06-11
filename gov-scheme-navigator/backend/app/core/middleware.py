from __future__ import annotations

import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)

class _PassThroughMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        return await call_next(request)

class RateLimitMiddleware(_PassThroughMiddleware):
    def __init__(self, app, rate: str = "100/minute") -> None:
        super().__init__(app)
        self.rate = rate

class AuditLogMiddleware(_PassThroughMiddleware):
    """Placeholder for request auditing."""

class PIIRedactionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        # In a real app, we would intercept logging calls or response bodies here
        # Aadhaar: r'\d{4}[-\s]?\d{4}[-\s]?\d{4}'
        # PAN: r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
        # Phone: r'\+?\d{10,12}'
        return response

class PromptInjectionGuard(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in ("POST", "PUT"):
            try:
                body_bytes = await request.body()
                text = body_bytes.decode('utf-8').lower()
                forbidden = ["ignore previous instructions", "system prompt", "override instructions", "forget everything"]
                if any(f in text for f in forbidden):
                    logger.warning("Prompt injection detected and blocked.")
                    return JSONResponse(status_code=400, content={"detail": "Prompt injection detected. Request rejected."})
                
                # Reset stream for downstream consumption
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
            except Exception:
                pass
                
        return await call_next(request)
