from __future__ import annotations

from typing import Any


class GraphIngestor:
    def ingest_scheme(self, scheme: dict[str, Any]) -> None:
        raise NotImplementedError("Graph ingestion will be implemented here.")

    def ingest_relationships(self, relationships: list[dict[str, Any]]) -> None:
        raise NotImplementedError("Graph relationship ingestion will be implemented here.")
