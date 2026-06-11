from __future__ import annotations

from typing import Any, Mapping, Sequence


class VectorStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def upsert_chunks(self, chunks: Sequence[Mapping[str, Any]]) -> None:
        raise NotImplementedError("pgVector persistence will be implemented here.")

    async def search(self, query: str, top_k: int = 10) -> list[Mapping[str, Any]]:
        raise NotImplementedError("Vector search will be implemented here.")

    async def refresh_index(self) -> None:
        raise NotImplementedError("Index management will be implemented here.")
