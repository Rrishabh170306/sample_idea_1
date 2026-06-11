from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class RetrievalHit:
    content: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    def retrieve(self, query: str, user_profile: Mapping[str, Any] | None = None) -> list[RetrievalHit]:
        raise NotImplementedError("Hybrid retrieval will be implemented here.")

    def vector_search(self, query: str, top_k: int = 20) -> list[RetrievalHit]:
        raise NotImplementedError("Vector retrieval will be implemented here.")

    def bm25_search(self, query: str, top_k: int = 20) -> list[RetrievalHit]:
        raise NotImplementedError("Keyword retrieval will be implemented here.")

    def graph_query(self, query: str, top_k: int = 10) -> list[RetrievalHit]:
        raise NotImplementedError("Graph traversal will be implemented here.")
