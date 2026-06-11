from __future__ import annotations

import asyncio
import logging
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class GraphAgent:
    def __init__(self, graph_orchestrator=None, timeout_seconds: int = 5):
        self.graph_orchestrator = graph_orchestrator
        self.timeout_seconds = timeout_seconds

    async def query(self, state: AgentState) -> dict:
        query = state.get("query", "")
        profile = state.get("user_profile", {})

        if not query:
            return {"graph_results": []}

        try:
            if self.graph_orchestrator:
                results = await asyncio.wait_for(
                    self.graph_orchestrator.hybrid_search(query=query, user_profile=profile, top_k=5),
                    timeout=self.timeout_seconds,
                )
                results_dict = [
                    {"score": float(getattr(r, "score", 1.0)), "node": getattr(r, "node", None)} for r in results
                ]
            else:
                results_dict = [{"node": "Mock Graph Node", "relationship": "MOCK_REL", "score": 1.0}]

            return {"graph_results": results_dict}

        except asyncio.TimeoutError:
            logger.warning("Graph query timeout for query: %s", query)
            return {"graph_results": [], "error": "graph_query_timeout"}
        except Exception as exc:
            logger.exception("Graph query failed: %s", exc)
            return {"graph_results": [], "error": str(exc)}
