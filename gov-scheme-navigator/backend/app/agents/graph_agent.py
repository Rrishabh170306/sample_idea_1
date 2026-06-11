from __future__ import annotations

from typing import Any


class GraphAgent:
    def query(self, query: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("Graph querying will be implemented here.")
