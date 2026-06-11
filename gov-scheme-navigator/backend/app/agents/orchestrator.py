from __future__ import annotations

from typing import Any

from app.agents.state import AgentState


class Orchestrator:
    def build_graph(self) -> dict[str, Any]:
        raise NotImplementedError("LangGraph orchestration will be implemented here.")

    def run(self, state: AgentState) -> AgentState:
        raise NotImplementedError("Orchestration runtime will be implemented here.")
