"""Async SQLAlchemy engine and session factory.

Usage:
    from app.db.session import get_db, engine

    async with get_db() as session:
        result = await session.execute(...)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base

logger = logging.getLogger(__name__)


def _build_async_url(url: str) -> str:
    """Ensure the DSN uses the asyncpg driver."""
    if not url:
        return url
    if "asyncpg" in url:
        return url
    url = url.replace("postgresql+psycopg2", "postgresql+asyncpg")
    url = url.replace("postgresql+psycopg", "postgresql+asyncpg")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _get_database_url() -> str:
    return _build_async_url(os.getenv("DATABASE_URL", ""))


def _create_engine():
    url = _get_database_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Set it to a PostgreSQL connection string before starting the application."
        )
    return create_async_engine(
        url,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# Lazy engine — only created when first needed
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _SessionLocal


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables (used for dev/testing when Alembic is not used)."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Enable pgvector if available
        try:
            await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            logger.warning("Could not create pgvector extension — ensure it is installed")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised")


async def dispose_engine() -> None:
    """Dispose the async engine (call on app shutdown)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")
