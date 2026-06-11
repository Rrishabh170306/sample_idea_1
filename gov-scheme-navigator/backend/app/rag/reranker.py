from __future__ import annotations

from typing import Sequence

from app.rag.retriever import RetrievalHit


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name

    def rerank(self, query: str, candidates: Sequence[RetrievalHit], top_k: int = 5) -> list[RetrievalHit]:
        raise NotImplementedError("Cross-encoder reranking will be implemented here.")
