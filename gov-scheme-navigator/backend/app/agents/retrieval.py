from __future__ import annotations

from typing import Any


class RetrievalAgent:
    def retrieve(self, query: str, user_profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("Hybrid retrieval orchestration will be implemented here.")
