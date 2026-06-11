from __future__ import annotations

from typing import Any


class DocumentAgent:
    def process(self, file_path: str) -> dict[str, Any]:
        raise NotImplementedError("Document processing will be implemented here.")
