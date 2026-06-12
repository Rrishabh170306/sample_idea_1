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

        if self.graph_orchestrator is None:
            return {
                "graph_results": [],
                "error_code": "graph_not_configured",
                "error": "No graph orchestrator dependency was injected.",
            }

        try:
            results = await asyncio.wait_for(
                self.graph_orchestrator.hybrid_search(query=query, user_profile=profile, top_k=5),
                timeout=self.timeout_seconds,
            )
            results_dict = [
                {
                    "scheme_id": getattr(r, "scheme_id", ""),
                    "name": getattr(r, "name", ""),
                    "source": getattr(r, "source", "graph"),
                    "score": float(getattr(r, "relevance_score", getattr(r, "score", 1.0))),
                    "metadata": getattr(r, "metadata", {}) or {},
                }
                for r in results
            ]

            return {"graph_results": results_dict}

        except asyncio.TimeoutError:
            logger.warning("Graph query timeout for query: %s", query)
            return {"graph_results": [], "error": "graph_query_timeout"}
        except Exception as exc:
            logger.exception("Graph query failed: %s", exc)
            return {"graph_results": [], "error": str(exc)}
