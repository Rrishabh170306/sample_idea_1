from __future__ import annotations

from typing import Sequence

from app.rag.retriever import RetrievalHit

class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError:
                raise ImportError("Please install sentence-transformers: pip install sentence-transformers")
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, candidates: Sequence[RetrievalHit], top_k: int = 5) -> list[RetrievalHit]:
        if not candidates:
            return []
            
        pairs = [[query, hit.content] for hit in candidates]
        scores = self.model.predict(pairs)
        
        # We create new RetrievalHit objects or modify existing ones.
        # Since RetrievalHit is a dataclass without frozen=True, we can modify in place.
        for hit, score in zip(candidates, scores):
            hit.score = float(score)
            
        ranked_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)
        return list(ranked_candidates[:top_k])
