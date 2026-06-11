from __future__ import annotations

from typing import Annotated, Any, Sequence, TypedDict

try:
    from langgraph.graph.message import add_messages
    from langchain_core.messages import BaseMessage
except ImportError:
    # Fallback/mock if packages are not installed yet
    def add_messages(left, right):
        return left + right
    BaseMessage = Any

class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    query_type: str  # eligibility|comparison|application|document|general
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
