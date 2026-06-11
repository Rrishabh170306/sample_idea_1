from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    query: str
    query_type: str
    user_profile: dict[str, Any]
    retrieved_chunks: list[dict[str, Any]]
    graph_results: list[dict[str, Any]]
    eligibility_results: dict[str, Any]
    citations: list[dict[str, Any]]
    confidence_score: float
    needs_human_review: bool
    response: str
    session_id: str
    turn_count: int
