from __future__ import annotations

from typing import Any


def format_citation(claim: str, source_url: str, source_text: str, confidence: float) -> dict[str, Any]:
    return {
        "claim": claim,
        "source_url": source_url,
        "source_text": source_text,
        "confidence": confidence,
    }


class CitationAgent:
    def attach(self, response: str) -> dict[str, Any]:
        raise NotImplementedError("Citation attachment will be implemented here.")
