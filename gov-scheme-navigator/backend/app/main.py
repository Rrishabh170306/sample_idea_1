from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting %s v%s", settings.app_name, settings.version)

    # Prometheus metrics (optional)
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "0") or 0)
    init_observability(prometheus_port=prometheus_port if prometheus_port else None)

    # Initialize database (run migrations via alembic in entrypoint.sh;
    # here we just ensure the session factory is ready)
    if settings.database_url:
        try:
            from app.db.session import get_engine
            engine = get_engine()
            # Quick connectivity probe
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
        except Exception as exc:
            logger.error("Database connection failed: %s — continuing without DB", exc)
    else:
        logger.warning("DATABASE_URL not set — running without persistent database")

    # Seed in-memory graph with fixture schemes so the agent can respond
    # even before the scraper runs
    try:
        from app.agents.dependencies import _async_seed_graph
        await _async_seed_graph()
        logger.info("In-memory knowledge graph seeded")
    except Exception as exc:
        logger.warning("Graph seeding failed: %s", exc)

    # Ensure Neo4j constraints exist
    try:
        from app.graph.ingestion import GraphIngestor
        ingestor = GraphIngestor()
        await ingestor.ensure_constraints()
        logger.info("Neo4j constraints verified")
    except Exception as exc:
        logger.warning("Neo4j constraint setup failed: %s — Neo4j may not be ready", exc)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down %s", settings.app_name)
    try:
        from app.db.session import dispose_engine
        await dispose_engine()
    except Exception:
        pass


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
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


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.version}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check — returns 200 when the app is running."""
    checks: dict[str, str] = {"status": "ok"}

    # Check DB
    if settings.database_url:
        try:
            from app.db.session import get_engine
            from sqlalchemy import text
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    return checks
