from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from app.scraping.spiders.myscheme_spider import MySchemeSpider
from app.scraping.spiders.state_portal_spider import StatePortalSpider
from app.scraping.extractors.scheme_extractor import SchemeExtractor
from app.scraping.pipelines import NormalizeItemPipeline
from app.scraping.change_detector import ChangeDetector
from app.rag.chunker import Chunker
from app.rag.embedder import EmbeddingService
from app.db.vector_store import VectorStore
from app.graph.ingestion import GraphIngestor
from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_content(url: str) -> str:
    """Try Playwright rendering first, fall back to httpx GET."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            await asyncio.sleep(1)
            content = await page.content()
            await browser.close()
            return content
    except Exception:
        logger.debug("Playwright unavailable or failed for %s, using HTTP fallback", url)

    try:
        import httpx

        resp = httpx.get(url, timeout=30.0)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:  # pragma: no cover - network fallback
        logger.exception("Failed to fetch %s: %s", url, exc)
        raise


def _to_async_dsn(dsn: str) -> str:
    """Convert common postgres DSN to an async-friendly one if needed."""
    if not dsn:
        return dsn
    if "asyncpg" in dsn:
        return dsn
    # Replace common psycopg scheme with asyncpg
    return dsn.replace("postgresql+psycopg", "postgresql+asyncpg")


async def process_url(
    url: str,
    extractor: SchemeExtractor,
    normalize: NormalizeItemPipeline,
    detector: ChangeDetector,
    chunker: Chunker,
    embedder: EmbeddingService,
    vector_store: VectorStore,
    graph_ingestor: GraphIngestor,
) -> None:
    try:
        content = await fetch_content(url)

        change = await detector.has_changed(url, content)
        if not change.changed:
            logger.info("No change detected for %s — skipping ingestion", url)
            return

        extraction = extractor.extract(content, source_url=url)
        scheme = extraction.record.model_dump()
        scheme["official_url"] = scheme.get("official_url") or url

        # Normalize
        normalized = normalize.process_item(scheme)

        # Store in DB
        try:
            from app.db.session import get_session_factory
            from app.scraping.pipelines import StoragePipeline
            session_factory = get_session_factory()
            if session_factory:
                async with session_factory() as db_session:
                    storage = StoragePipeline(db_session=db_session, embedding_service=embedder)
                    await storage.process_item(normalized)
        except Exception as exc:
            logger.warning("DB storage failed, continuing with graph/vector ingestion: %s", exc)

        # Chunk
        chunks = chunker.chunk_parent_child(content)
        texts = [c.content for c in chunks]
        if not texts:
            logger.warning("No chunks generated for %s", url)
            return

        # Embed (run in threadpool to avoid blocking event loop)
        try:
            embeddings = await asyncio.to_thread(embedder.embed_texts, texts)
        except Exception:
            logger.exception("Embedding failed — using fallback hashing embeddings")
            import hashlib

            embeddings = []
            for t in texts:
                h = hashlib.sha256(t.encode("utf-8")).digest()
                vec = [float(b) for b in h]
                vec = (vec * (384 // len(vec) + 1))[:384]
                embeddings.append(vec)

        # Prepare chunk records
        records = []
        for chunk, emb in zip(chunks, embeddings):
            records.append(
                {
                    "id": chunk.id,
                    "scheme_id": normalized.get("scheme_id", "unknown"),
                    "content": chunk.content,
                    "chunk_type": chunk.chunk_type,
                    "parent_chunk_id": chunk.parent_id,
                    "embedding": emb,
                    "metadata": chunk.metadata,
                }
            )

        # Upsert into vector store
        await vector_store.upsert_chunks(records)

        # Ingest to knowledge graph
        await graph_ingestor.ingest_scheme(normalized)

        logger.info("Ingested and indexed scheme %s", normalized.get("scheme_id"))

    except Exception as exc:
        logger.exception("Failed to process %s: %s", url, exc)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    extractor = SchemeExtractor()
    normalize = NormalizeItemPipeline()
    detector = ChangeDetector()
    chunker = Chunker()

    # Embedding service: fallback to lightweight hashing if unavailable
    try:
        embedder = EmbeddingService()
    except Exception:
        logger.exception("EmbeddingService unavailable; embeddings will be hashed")
        # Create a simple fallback wrapper

        class _Fallback:
            def embed_texts(self, texts):
                import hashlib

                out = []
                for t in texts:
                    h = hashlib.sha256(t.encode("utf-8")).digest()
                    vec = [float(b) for b in h]
                    vec = (vec * (384 // len(vec) + 1))[:384]
                    out.append(vec)
                return out

        embedder = _Fallback()

    # Vector store (ensure async driver in DSN)
    dsn = _to_async_dsn(getattr(settings, "database_url", ""))
    vector_store = VectorStore(dsn)

    graph_ingestor = GraphIngestor()

    # Collect start URLs from available spiders
    spiders = [MySchemeSpider(), StatePortalSpider()]
    urls: list[str] = []
    for sp in spiders:
        try:
            urls.extend(getattr(sp, "start_urls", []))
        except Exception:
            continue

    async def run_once() -> None:
        # Process URLs concurrently but with a small concurrency limit
        sem = asyncio.Semaphore(4)

        async def sem_task(u: str):
            async with sem:
                await process_url(u, extractor, normalize, detector, chunker, embedder, vector_store, graph_ingestor)

        tasks = [asyncio.create_task(sem_task(u)) for u in urls]
        if tasks:
            await asyncio.gather(*tasks)
        else:
            logger.warning("No start URLs found for spiders — nothing to crawl")

    interval = getattr(settings, "scrape_interval_seconds", 0)
    if interval and int(interval) > 0:
        logger.info("Starting periodic scraper: interval=%s seconds", interval)
        while True:
            await run_once()
            logger.info("Sleeping %s seconds before next scrape", interval)
            await asyncio.sleep(int(interval))
    else:
        # Single-run mode
        await run_once()


class ScrapingRunner:
    """Callable wrapper for use from admin trigger or external code."""

    async def run(self, urls: list[str] | None = None) -> None:
        """Run the full scraping pipeline.

        Args:
            urls: Optional explicit list of URLs to scrape.
                  If None, uses the default spider start_urls.
        """
        if urls:
            # Run only the specified URLs
            extractor = SchemeExtractor()
            normalize = NormalizeItemPipeline()
            detector = ChangeDetector()
            chunker = Chunker()
            embedder = EmbeddingService()
            dsn = _to_async_dsn(getattr(settings, "database_url", ""))
            vector_store = VectorStore(dsn)
            graph_ingestor = GraphIngestor()

            sem = asyncio.Semaphore(4)

            async def sem_task(u: str):
                async with sem:
                    await process_url(u, extractor, normalize, detector, chunker,
                                      embedder, vector_store, graph_ingestor)

            tasks = [asyncio.create_task(sem_task(u)) for u in urls]
            if tasks:
                await asyncio.gather(*tasks)
        else:
            await main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Runner interrupted")
