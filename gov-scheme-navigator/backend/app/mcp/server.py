from __future__ import annotations

import json
import logging

try:
    from mcp.server.fastmcp import FastMCP
    mcp_installed = True
except ImportError:
    mcp_installed = False
    class FastMCP:
        def __init__(self, name):
            self.name = name
            self.tools = []
        def tool(self):
            def decorator(func):
                self.tools.append(func)
                return func
            return decorator
        def run(self):
            print(f"Mock MCP Server '{self.name}' running. (Install 'mcp' package for real server)")

from app.rag.retriever import HybridRetriever
from app.eligibility.engine import EligibilityEngine
import asyncio
import time

try:
    from app.core.observability import REQUEST_COUNTER, REQUEST_LATENCY
except Exception:
    from typing import Any, Optional
    REQUEST_COUNTER: Optional[Any] = None
    REQUEST_LATENCY: Optional[Any] = None

logger = logging.getLogger(__name__)

# Initialize the FastMCP server
mcp = FastMCP("GovSchemeNavigator")

# Initialize components lazily; concrete instances should be provided in app startup
retriever: HybridRetriever | None = None
eligibility_engine = EligibilityEngine()

@mcp.tool()
async def search_schemes(query: str, profile_filter: str = "") -> dict:
    """Search for government schemes using semantic query and optional profile filters."""
    profile = {}
    if profile_filter:
        try:
            profile = json.loads(profile_filter)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON passed to profile_filter")
            return {"error": "invalid_profile_json"}

    # If retriever is not configured, return a clear error
    if retriever is None:
        logger.warning("Hybrid retriever not configured for MCP server")
        return {"error": "retriever_not_configured"}

    try:
        start = time.time()
        hits = await asyncio.wait_for(retriever.retrieve(query, user_profile=profile), timeout=10)
        latency = round(time.time() - start, 3)

        if REQUEST_COUNTER:
            try:
                REQUEST_COUNTER.labels(endpoint="mcp_search", method="search_schemes", status="ok").inc()
            except Exception:
                pass
        if REQUEST_LATENCY:
            try:
                REQUEST_LATENCY.labels(endpoint="mcp_search").observe(latency)
            except Exception:
                pass

        return {"results": [h.__dict__ for h in hits], "latency_s": latency}
    except asyncio.TimeoutError:
        logger.warning("MCP search timeout for query: %s", query)
        return {"error": "retrieval_timeout"}
    except Exception as exc:
        logger.exception("Error during MCP search: %s", exc)
        return {"error": str(exc)}

@mcp.tool()
async def check_eligibility(user_profile_json: str, scheme_rules_json: str) -> dict:
    """Evaluate a user profile against scheme rules to determine eligibility."""
    try:
        profile = json.loads(user_profile_json)
        rules = json.loads(scheme_rules_json)
        result = eligibility_engine.evaluate(profile, rules)

        return {
            "eligible": result.eligible,
            "score": result.score,
            "gaps": result.gaps,
            "explanation": result.explanation,
        }
    except json.JSONDecodeError:
        logger.exception("Invalid JSON provided to check_eligibility")
        return {"error": "invalid_json"}
    except Exception as e:
        logger.exception("Error evaluating eligibility: %s", e)
        return {"error": str(e)}

@mcp.tool()
async def get_scheme_details(scheme_id: str) -> dict:
    """Retrieve deep graph information for a specific scheme."""
    # In production this would query Neo4j for a full subgraph; returning structured placeholder
    return {"scheme_id": scheme_id, "details": "mocked_relationship_data"}

if __name__ == "__main__":
    mcp.run()
