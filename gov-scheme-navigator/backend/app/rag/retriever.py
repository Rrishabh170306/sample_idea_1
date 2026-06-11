from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Mapping

from app.db.vector_store import VectorStore
from app.rag.embedder import EmbeddingService
from app.rag.reranker import CrossEncoderReranker
import logging

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalHit:
    content: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    def __init__(self, vector_store: VectorStore, embedder: EmbeddingService, reranker: CrossEncoderReranker):
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker

    async def retrieve(self, query: str, user_profile: Mapping[str, Any] | None = None, top_k: int = 5) -> list[RetrievalHit]:
        # Validate inputs
        if not query:
            return []

        top_k = max(1, min(int(top_k), 100))

        # 1. Multi-Query Expansion (Mocked for now - ideally LLM generates these)
        queries = [query]
        # In a real system: queries = await self.expand_query(query)
        
        # 2. Parallel Retrieval
        vector_hits = []
        bm25_hits = []
        
        for q in queries:
            v_hits, b_hits = await asyncio.gather(
                self.vector_search(q, top_k=20),
                self.bm25_search(q, top_k=20),
                return_exceptions=True,
            )
            if not isinstance(v_hits, Exception):
                vector_hits.extend(v_hits)
            if not isinstance(b_hits, Exception):
                bm25_hits.extend(b_hits)
            
        # Graph query based on user profile
        graph_hits = await self.graph_query(query, user_profile, top_k=10)
        
        # 3. RRF Fusion
        fused_hits = self._reciprocal_rank_fusion([vector_hits, bm25_hits, graph_hits])
        
        # 4. Cross-Encoder Reranking
        candidates = [hit for hit in fused_hits][:200]
        try:
            reranked_hits = self.reranker.rerank(query, candidates, top_k=top_k)
        except Exception as exc:
            logger.exception("Reranker failed, returning fused candidates: %s", exc)
            reranked_hits = list(candidates)[:top_k]

        return reranked_hits

    async def vector_search(self, query: str, top_k: int = 20) -> list[RetrievalHit]:
        try:
            query_embedding = self.embedder.embed_query(query)
        except Exception as exc:
            logger.exception("Embedding query failed: %s", exc)
            return []

        results = await self.vector_store.vector_search(query_embedding, top_k=top_k)
        return [RetrievalHit(content=r["content"], score=r["score"], metadata=r["metadata"]) for r in results]

    async def bm25_search(self, query: str, top_k: int = 20) -> list[RetrievalHit]:
        results = await self.vector_store.bm25_search(query, top_k=top_k)
        return [RetrievalHit(content=r["content"], score=r["score"], metadata=r.get("metadata", {})) for r in results]

    async def graph_query(self, query: str, user_profile: Mapping[str, Any] | None = None, top_k: int = 10) -> list[RetrievalHit]:
        # Graph traversal will be implemented here. For now, returning empty.
        return []
        
    def _reciprocal_rank_fusion(self, list_of_hits: list[list[RetrievalHit]], k: int = 60) -> list[RetrievalHit]:
        rrf_scores: dict[str, RetrievalHit] = {}
        
        for hits in list_of_hits:
            for rank, hit in enumerate(hits, start=1):
                # Prefer explicit id in metadata, fall back to content
                doc_id = hit.metadata.get("id") if isinstance(hit.metadata, dict) and hit.metadata.get("id") else hit.content
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = RetrievalHit(content=hit.content, score=0.0, metadata=hit.metadata)

                rrf_scores[doc_id].score += 1.0 / (k + rank)
                
        sorted_fused = sorted(rrf_scores.values(), key=lambda x: x.score, reverse=True)
        return sorted_fused
