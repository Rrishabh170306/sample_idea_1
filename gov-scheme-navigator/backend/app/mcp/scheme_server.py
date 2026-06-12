"""MCP Scheme Server — exposes scheme search as MCP tools."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SchemeSearchTool:
    """MCP tool: search for schemes by query and profile."""

    name = "search_schemes"
    description = (
        "Search government schemes by free-text query and user profile attributes. "
        "Returns a list of matching schemes with benefit details and eligibility criteria."
    )

    async def run(
        self,
        query: str,
        state: str | None = None,
        occupation: str | None = None,
        category: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Execute a scheme search.

        Args:
            query: Natural language search query
            state: User's state (e.g. "Tamil Nadu", "Central")
            occupation: User's occupation (e.g. "farmer", "student")
            category: Caste/social category (e.g. "SC", "OBC")
            top_k: Maximum number of results

        Returns:
            Dict with 'schemes' list and 'total' count
        """
        user_profile = {}
        if state:
            user_profile["state"] = state
        if occupation:
            user_profile["occupation"] = occupation
        if category:
            user_profile["category"] = category

        results: list[dict[str, Any]] = []

        # Try Neo4j first
        if state:
            try:
                from app.graph.ingestion import GraphIngestor
                ingestor = GraphIngestor()
                neo4j_results = await ingestor.query_schemes_for_profile(
                    state=state,
                    occupation=occupation,
                    category=category,
                    top_k=top_k,
                )
                results.extend(neo4j_results)
            except Exception as exc:
                logger.debug("Neo4j search failed: %s", exc)

        # Supplement with in-memory graph
        if len(results) < top_k:
            try:
                from app.agents.dependencies import get_graph_orchestrator
                orchestrator = get_graph_orchestrator()
                if orchestrator:
                    search_results = await orchestrator.hybrid_search(
                        query, user_profile, top_k=top_k
                    )
                    for r in search_results:
                        results.append({
                            "scheme_id": getattr(r, "scheme_id", ""),
                            "name": getattr(r, "name", ""),
                            "relevance_score": float(getattr(r, "relevance_score", 0.5)),
                            "source": getattr(r, "source", "graph"),
                        })
            except Exception as exc:
                logger.debug("In-memory graph search failed: %s", exc)

        return {"schemes": results[:top_k], "total": len(results)}


class SchemeDetailTool:
    """MCP tool: get full details for a specific scheme by ID."""

    name = "get_scheme_detail"
    description = "Retrieve complete details for a government scheme by its ID."

    async def run(self, scheme_id: str) -> dict[str, Any]:
        """Get scheme detail from PostgreSQL.

        Args:
            scheme_id: The unique scheme identifier

        Returns:
            Dict with full scheme data or error
        """
        try:
            from app.db.session import get_db
            from app.db.models import Scheme
            from sqlalchemy import select

            async with get_db() as session:
                result = await session.execute(
                    select(Scheme).where(Scheme.scheme_id == scheme_id)
                )
                scheme = result.scalar_one_or_none()
                if scheme is None:
                    return {"error": f"Scheme '{scheme_id}' not found"}

                return {
                    "scheme_id": scheme.scheme_id,
                    "name": scheme.name,
                    "name_hindi": scheme.name_hindi,
                    "department": scheme.department,
                    "ministry": scheme.ministry,
                    "state": scheme.state,
                    "category": scheme.category,
                    "target_beneficiaries": scheme.target_beneficiaries,
                    "eligibility": scheme.eligibility,
                    "benefits": scheme.benefits,
                    "documents_required": scheme.documents_required,
                    "application_process": scheme.application_process,
                    "official_url": scheme.official_url,
                    "status": scheme.status,
                }
        except Exception as exc:
            logger.exception("SchemeDetailTool failed: %s", exc)
            return {"error": str(exc)}


class SchemeMCPServer:
    """MCP server exposing scheme search and detail tools."""

    def __init__(self):
        self.tools = {
            SchemeSearchTool.name: SchemeSearchTool(),
            SchemeDetailTool.name: SchemeDetailTool(),
        }

    async def handle(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(tool_name)
        if tool is None:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return await tool.run(**params)
        except Exception as exc:
            logger.exception("MCP tool %s failed: %s", tool_name, exc)
            return {"error": str(exc)}

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": t.name, "description": t.description}
            for t in self.tools.values()
        ]
