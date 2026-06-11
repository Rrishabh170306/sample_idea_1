from __future__ import annotations

from typing import Any
from app.agents.state import AgentState

def format_citation(claim: str, source_url: str, source_text: str, confidence: float) -> dict[str, Any]:
    return {
        "claim": claim,
        "source_url": source_url,
        "source_text": source_text,
        "confidence": confidence,
    }

class CitationAgent:
    def attach(self, state: AgentState) -> dict:
        chunks = state.get("retrieved_chunks", [])
        citations = []
        for i, chunk in enumerate(chunks[:3]):
            citations.append(format_citation(
                claim=f"Claim derived from chunk {i}",
                source_url=chunk.get("metadata", {}).get("source", "https://scheme.gov.in/source"),
                source_text=chunk.get("content", "")[:50],
                confidence=0.9
            ))
        return {"citations": citations}
