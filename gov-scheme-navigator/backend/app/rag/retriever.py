from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from app.db.vector_store import VectorStore
from app.rag.embedder import EmbeddingService
from app.rag.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalHit:
    content: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    """Hybrid retriever: vector search + BM25 + Neo4j graph + RRF fusion + cross-encoder rerank."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingService,
        reranker: CrossEncoderReranker,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        user_profile: Mapping[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        if not query:
            return []

        top_k = max(1, min(int(top_k), 100))

        # 1. Parallel retrieval — vector, BM25, graph
        vector_task = asyncio.create_task(self.vector_search(query, top_k=20))
        bm25_task = asyncio.create_task(self.bm25_search(query, top_k=20))
        graph_task = asyncio.create_task(self.graph_query(query, user_profile, top_k=10))

        vector_hits, bm25_hits, graph_hits = await asyncio.gather(
            vector_task, bm25_task, graph_task, return_exceptions=True
        )

        all_lists: list[list[RetrievalHit]] = []
        for hits in (vector_hits, bm25_hits, graph_hits):
            if isinstance(hits, Exception):
                logger.warning("Retrieval sub-task failed: %s", hits)
                all_lists.append([])
            else:
                all_lists.append(hits)  # type: ignore[arg-type]

        # 2. RRF fusion
        fused = self._reciprocal_rank_fusion(all_lists)

        # 3. Cross-encoder reranking
        candidates = fused[:200]
        try:
            reranked = self.reranker.rerank(query, candidates, top_k=top_k)
        except Exception as exc:
            logger.warning("Reranker failed, using fused order: %s", exc)
            reranked = candidates[:top_k]

        return reranked

    async def vector_search(self, query: str, top_k: int = 20) -> list[RetrievalHit]:
        try:
            query_embedding = await asyncio.to_thread(self.embedder.embed_query, query)
        except Exception as exc:
            logger.warning("Embedding failed: %s", exc)
            return []

        results = await self.vector_store.vector_search(query_embedding, top_k=top_k)
        return [
            RetrievalHit(
                content=r["content"],
                score=float(r.get("score", 1.0)),
                source="vector",
                metadata=r.get("metadata", {}),
            )
            for r in results
        ]

    async def bm25_search(self, query: str, top_k: int = 20) -> list[RetrievalHit]:
        results = await self.vector_store.bm25_search(query, top_k=top_k)
        return [
            RetrievalHit(
                content=r["content"],
                score=float(r.get("score", 1.0)),
                source="bm25",
                metadata=r.get("metadata", {}),
            )
            for r in results
        ]

    async def graph_query(
        self,
        query: str,
        user_profile: Mapping[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[RetrievalHit]:
        """Query Neo4j knowledge graph for schemes matching the user profile.

        Falls back to the in-memory graph orchestrator if Neo4j is unavailable.
        """
        hits: list[RetrievalHit] = []
        profile = dict(user_profile or {})

        # ── Try Neo4j first ────────────────────────────────────────────────
        state = profile.get("state", "")
        if state:
            try:
                from app.graph.ingestion import GraphIngestor
                ingestor = GraphIngestor()
                neo4j_results = await ingestor.query_schemes_for_profile(
                    state=state,
                    occupation=profile.get("occupation"),
                    category=profile.get("category"),
                    top_k=top_k,
                )
                for r in neo4j_results:
                    name = r.get("name") or r.get("scheme_id", "")
                    hits.append(
                        RetrievalHit(
                            content=f"Scheme: {name}",
                            score=0.85,
                            source="neo4j",
                            metadata={
                                "id": r.get("scheme_id", ""),
                                "scheme_name": name,
                                "source": "neo4j",
                                "official_url": r.get("official_url", ""),
                            },
                        )
                    )
                if hits:
                    logger.info("Neo4j graph_query returned %d hits for state=%s", len(hits), state)
                    return hits
            except Exception as exc:
                logger.debug("Neo4j graph_query failed: %s", exc)

        # ── Fallback: in-memory KnowledgeGraphOrchestrator ────────────────
        try:
            from app.agents.dependencies import get_graph_orchestrator
            orchestrator = get_graph_orchestrator()
            if orchestrator is None:
                return []

            search_results = await orchestrator.hybrid_search(
                query, profile, top_k=top_k
            )
            for result in search_results:
                name = getattr(result, "name", "") or ""
                scheme_id = getattr(result, "scheme_id", "") or ""
                score = float(getattr(result, "relevance_score", 0.5))
                hits.append(
                    RetrievalHit(
                        content=f"Scheme: {name}",
                        score=score,
                        source="in_memory_graph",
                        metadata={
                            "id": scheme_id,
                            "scheme_name": name,
                            "source": "graph",
                        },
                    )
                )
        except Exception as exc:
            logger.debug("In-memory graph_query failed: %s", exc)

        return hits

    def _reciprocal_rank_fusion(
        self,
        list_of_hits: list[list[RetrievalHit]],
        k: int = 60,
    ) -> list[RetrievalHit]:
        """Reciprocal Rank Fusion: RRF(d) = Σ 1 / (k + rank(d))."""
        rrf_scores: dict[str, RetrievalHit] = {}

        for hits in list_of_hits:
            for rank, hit in enumerate(hits, start=1):
                doc_id = (
                    hit.metadata.get("id")
                    if isinstance(hit.metadata, dict) and hit.metadata.get("id")
                    else hit.content[:100]
                )
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = RetrievalHit(
                        content=hit.content,
                        score=0.0,
                        source=hit.source,
                        metadata=hit.metadata,
                    )
                rrf_scores[doc_id].score += 1.0 / (k + rank)

        return sorted(rrf_scores.values(), key=lambda x: x.score, reverse=True)
