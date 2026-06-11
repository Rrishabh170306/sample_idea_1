from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.profile import router as profile_router
from app.api.schemes import router as schemes_router
from app.api.admin import router as admin_router
from app.core.config import get_settings
from app.core.middleware import AuditLogMiddleware, PIIRedactionMiddleware, PromptInjectionGuard, RateLimitMiddleware
from app.core.observability import init_observability
import os


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, rate=settings.rate_limit)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(PIIRedactionMiddleware)
app.add_middleware(PromptInjectionGuard)

for router in (chat_router, schemes_router, documents_router, profile_router, admin_router):
    app.include_router(router, prefix=settings.api_prefix)


@app.on_event("startup")
async def on_startup() -> None:
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "0") or 0)
    # Only start the Prometheus HTTP server if a port is configured
    init_observability(prometheus_port=prometheus_port if prometheus_port else None)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.version}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
