from __future__ import annotations

from typing import Sequence


class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self.model_name = model_name

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError("Embedding generation will be implemented here.")

    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError("Query embedding will be implemented here.")
