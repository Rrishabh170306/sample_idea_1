from __future__ import annotations

import uuid
from typing import Any, Mapping, Sequence

try:
    from sqlalchemy import select, func, text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    _HAS_SQLALCHEMY = True
except Exception:
    # Allow importing this module in lightweight test environments without sqlalchemy.
    select = func = text = None  # type: ignore
    AsyncSession = object  # type: ignore
    create_async_engine = None
    sessionmaker = None
    _HAS_SQLALCHEMY = False

from app.db.models import SchemeChunk


class VectorStore:
    def __init__(self, dsn: str) -> None:
        if not _HAS_SQLALCHEMY:
            raise RuntimeError("SQLAlchemy is not available in the current environment; VectorStore cannot be used.")
        self.dsn = dsn
        self.engine = create_async_engine(dsn, echo=False)
        self.SessionLocal = sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def upsert_chunks(self, chunks: Sequence[Mapping[str, Any]]) -> None:
        async with self.SessionLocal() as session:
            for chunk_data in chunks:
                chunk_id = chunk_data.get("id") or str(uuid.uuid4())
                stmt = select(SchemeChunk).filter_by(id=chunk_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing.content = chunk_data["content"]
                    if "embedding" in chunk_data:
                        existing.embedding = chunk_data["embedding"]
                    existing.metadata_json = chunk_data.get("metadata", {})
                else:
                    new_chunk = SchemeChunk(
                        id=chunk_id,
                        scheme_id=chunk_data.get("scheme_id", "unknown"),
                        content=chunk_data["content"],
                        chunk_type=chunk_data.get("chunk_type", "child"),
                        parent_chunk_id=chunk_data.get("parent_chunk_id"),
                        embedding=chunk_data.get("embedding"),
                        metadata_json=chunk_data.get("metadata", {}),
                    )
                    session.add(new_chunk)
            
            # Simple approach: manually set search_vector after inserts
            # In production, a trigger should be used.
            await session.commit()
            
            # Update search_vector for BM25
            await session.execute(
                text("UPDATE scheme_chunks SET search_vector = to_tsvector('english', content) WHERE search_vector IS NULL")
            )
            await session.commit()

    async def vector_search(self, query_embedding: list[float], top_k: int = 10) -> list[Mapping[str, Any]]:
        async with self.SessionLocal() as session:
            try:
                if not query_embedding:
                    return []

                # Limit top_k to a sane maximum
                top_k = min(int(top_k), 100)

                stmt = (
                    select(SchemeChunk)
                    .order_by(SchemeChunk.embedding.cosine_distance(query_embedding))
                    .limit(top_k)
                )
                result = await session.execute(stmt)
                chunks = result.scalars().all()

                out = []
                for c in chunks:
                    score = getattr(c, "score", None) or 1.0
                    out.append({
                        "id": c.id,
                        "scheme_id": c.scheme_id,
                        "content": c.content,
                        "metadata": c.metadata_json or {},
                        "score": float(score),
                    })

                return out
            except Exception as exc:
                # Log and return empty list on errors
                import logging
                logging.getLogger(__name__).exception("Vector search failed: %s", exc)
                return []

    async def bm25_search(self, query: str, top_k: int = 10) -> list[Mapping[str, Any]]:
        async with self.SessionLocal() as session:
            try:
                top_k = min(int(top_k), 500)
                stmt = (
                    select(SchemeChunk)
                    .filter(SchemeChunk.search_vector.op("@@")(func.plainto_tsquery("english", query)))
                    .limit(top_k)
                )
                result = await session.execute(stmt)
                chunks = result.scalars().all()

                return [
                    {
                        "id": c.id,
                        "scheme_id": c.scheme_id,
                        "content": c.content,
                        "metadata": c.metadata_json or {},
                        "score": 1.0,
                    }
                    for c in chunks
                ]
            except Exception as exc:
                import logging
                logging.getLogger(__name__).exception("BM25 search failed: %s", exc)
                return []

    async def refresh_index(self) -> None:
        # Placeholder for manual index recreation if needed
        pass
