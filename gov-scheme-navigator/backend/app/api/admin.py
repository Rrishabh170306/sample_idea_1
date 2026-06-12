from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Review Queue ──────────────────────────────────────────────────────────────

@router.get("/review_queue")
async def get_review_queue() -> list[dict[str, Any]]:
    """Fetch pending items from the Human-in-the-Loop review queue (DB)."""
    try:
        from app.db.session import get_db
        from app.db.models import ReviewQueue
        from sqlalchemy import select

        async with get_db() as session:
            result = await session.execute(
                select(ReviewQueue).where(ReviewQueue.status == "pending").limit(50)
            )
            items = result.scalars().all()
            return [
                {
                    "id": item.id,
                    "session_id": item.session_id,
                    "query": item.query,
                    "response": item.response,
                    "confidence": item.confidence,
                    "reason": item.reason,
                    "status": item.status,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in items
            ]
    except Exception as exc:
        logger.warning("DB unavailable, returning empty queue: %s", exc)
        return []


@router.post("/review/{item_id}/resolve")
async def resolve_review_item(item_id: str, action: str) -> dict[str, str]:
    """Resolve a pending queue item. Action must be 'approve' or 'reject'."""
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    try:
        from app.db.session import get_db
        from app.db.models import ReviewQueue
        from sqlalchemy import select
        from datetime import datetime, timezone

        async with get_db() as session:
            result = await session.execute(
                select(ReviewQueue).where(ReviewQueue.id == item_id)
            )
            item = result.scalar_one_or_none()
            if item is None:
                raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")
            item.status = action + "d"
            item.reviewed_at = datetime.now(timezone.utc)
            await session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to resolve review item %s: %s", item_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": f"Item {item_id} {action}d successfully."}


# ── Scraper Trigger ───────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    urls: list[str] | None = None
    spider: str = "state_portal"


async def _run_scrape_background(urls: list[str] | None, job_id: str) -> None:
    """Background task: runs the scraper pipeline."""
    logger.info("[job=%s] Scrape job started", job_id)
    try:
        from app.scraping.runner import ScrapingRunner
        runner = ScrapingRunner()
        await runner.run(urls=urls)
        logger.info("[job=%s] Scrape job completed", job_id)
    except Exception:
        logger.exception("[job=%s] Scrape job failed", job_id)


@router.post("/scrape/trigger")
async def trigger_scrape(
    payload: ScrapeRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Enqueue a scrape job to run in the background.

    POST /api/v1/admin/scrape/trigger
    Body: {"urls": ["https://..."], "spider": "state_portal"}
    """
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_scrape_background, payload.urls, job_id)
    logger.info("Scrape job %s enqueued (spider=%s, urls=%s)", job_id, payload.spider, payload.urls)
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Scrape job {job_id} enqueued. Check logs for progress.",
    }


# ── Graph Stats ───────────────────────────────────────────────────────────────

@router.get("/graph/stats")
async def get_graph_stats() -> dict[str, Any]:
    """Return statistics from the in-memory knowledge graph."""
    try:
        from app.agents.dependencies import get_graph_orchestrator
        orchestrator = get_graph_orchestrator()
        if orchestrator is None:
            return {"status": "not_initialized"}
        return orchestrator.get_graph_stats()
    except Exception as exc:
        logger.exception("Failed to get graph stats: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Health Detail ─────────────────────────────────────────────────────────────

@router.get("/health/detail")
async def health_detail() -> dict[str, Any]:
    """Detailed health check across all subsystems."""
    from app.core.config import get_settings
    settings = get_settings()

    checks: dict[str, Any] = {}

    # DB
    if settings.database_url:
        try:
            from app.db.session import get_engine
            from sqlalchemy import text
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
    else:
        checks["database"] = "not_configured"

    # Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # Neo4j
    try:
        from app.graph.ingestion import GraphIngestor
        ingestor = GraphIngestor()
        driver = ingestor._get_driver()
        if driver:
            async with driver.session() as sess:
                await sess.run("RETURN 1")
            await driver.close()
            checks["neo4j"] = "ok"
        else:
            checks["neo4j"] = "driver_unavailable"
    except Exception as exc:
        checks["neo4j"] = f"error: {exc}"

    # In-memory graph
    try:
        from app.agents.dependencies import get_graph_orchestrator
        og = get_graph_orchestrator()
        checks["in_memory_graph"] = "seeded" if og else "not_seeded"
    except Exception as exc:
        checks["in_memory_graph"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" or v in ("not_configured", "seeded") for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
