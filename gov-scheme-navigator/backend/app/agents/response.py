from __future__ import annotations

from typing import Any


def compose_response(answer: str, citations: list[dict[str, Any]]) -> str:
    citation_block = "\n".join(f"- {citation['source_url']}" for citation in citations)
    if citation_block:
        return f"{answer}\n\nSources:\n{citation_block}"
    return answer


class ResponseAgent:
    def generate(self, state: dict[str, Any]) -> str:
        raise NotImplementedError("Response generation will be implemented here.")
