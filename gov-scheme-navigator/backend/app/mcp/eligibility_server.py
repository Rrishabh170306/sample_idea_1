"""MCP Eligibility Server — exposes eligibility checking as MCP tools."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CheckEligibilityTool:
    """MCP tool: check eligibility for a specific scheme."""

    name = "check_eligibility"
    description = (
        "Check whether a user profile is eligible for a specific government scheme. "
        "Returns eligibility verdict, score, gaps and explanation."
    )

    async def run(
        self,
        scheme_id: str,
        user_profile: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Args:
            scheme_id: Scheme identifier to check eligibility for
            user_profile: Dict of user attributes (age, income, state, occupation, etc.)

        Returns:
            Dict with eligible (bool), score (float), gaps (list), explanation (str)
        """
        try:
            # Fetch scheme rules from DB
            scheme_rules = await self._fetch_scheme_rules(scheme_id)
            if not scheme_rules:
                return {
                    "eligible": False,
                    "score": 0.0,
                    "gaps": [],
                    "explanation": f"Scheme '{scheme_id}' not found in database.",
                }

            from app.eligibility.engine import EligibilityEngine
            engine = EligibilityEngine()
            result = engine.evaluate(user_profile, scheme_rules)

            return {
                "eligible": result.eligible,
                "score": result.score,
                "gaps": result.gaps,
                "explanation": result.explanation,
            }

        except Exception as exc:
            logger.exception("Eligibility check failed for %s: %s", scheme_id, exc)
            return {"error": str(exc)}

    async def _fetch_scheme_rules(self, scheme_id: str) -> dict[str, Any] | None:
        """Fetch eligibility rules for a scheme from PostgreSQL."""
        try:
            from app.db.session import get_db
            from app.db.models import Scheme
            from sqlalchemy import select

            async with get_db() as session:
                result = await session.execute(
                    select(Scheme).where(Scheme.scheme_id == scheme_id)
                )
                scheme = result.scalar_one_or_none()
                if scheme and scheme.eligibility:
                    return self._build_json_logic_rules(scheme.eligibility)
                return None
        except Exception as exc:
            logger.debug("DB fetch failed for %s: %s — trying in-memory", scheme_id, exc)

        # Fallback: in-memory fixture rules
        from app.agents.dependencies import DEFAULT_SCHEME_FIXTURES
        for s in DEFAULT_SCHEME_FIXTURES:
            if s["scheme_id"] == scheme_id:
                return self._build_json_logic_rules(s.get("eligibility", {}))
        return None

    def _build_json_logic_rules(self, eligibility: dict[str, Any]) -> dict[str, Any]:
        """Convert eligibility dict to JSONLogic rule format."""
        conditions: list[dict[str, Any]] = []

        age_min = eligibility.get("age_min")
        age_max = eligibility.get("age_max")
        income_max = eligibility.get("income_max")
        land_max = eligibility.get("land_hectares_max")
        states = eligibility.get("states", [])
        occupations = eligibility.get("occupation", [])

        if age_min is not None:
            conditions.append({">=": [{"var": "age"}, age_min]})
        if age_max is not None:
            conditions.append({"<=": [{"var": "age"}, age_max]})
        if income_max is not None:
            conditions.append({"<=": [{"var": "income"}, income_max]})
        if land_max is not None:
            conditions.append({"<=": [{"var": "land_hectares"}, land_max]})
        if states and "all" not in [s.lower() for s in states]:
            conditions.append({"in": [{"var": "state"}, states]})
        if occupations:
            conditions.append({"in": [{"var": "occupation"}, occupations]})

        if not conditions:
            return {"==": [1, 1]}  # Always true if no rules
        if len(conditions) == 1:
            return conditions[0]
        return {"and": conditions}


class BulkEligibilityTool:
    """MCP tool: check eligibility across multiple schemes at once."""

    name = "bulk_check_eligibility"
    description = (
        "Check eligibility for multiple schemes in one call. "
        "Returns a ranked list of schemes with eligibility scores."
    )

    async def run(
        self,
        scheme_ids: list[str],
        user_profile: dict[str, Any],
    ) -> dict[str, Any]:
        checker = CheckEligibilityTool()
        results = {}
        for sid in scheme_ids:
            results[sid] = await checker.run(sid, user_profile)

        ranked = sorted(
            [{"scheme_id": k, **v} for k, v in results.items() if "error" not in v],
            key=lambda x: (x.get("eligible", False), x.get("score", 0.0)),
            reverse=True,
        )
        return {"results": results, "ranked": ranked}


class EligibilityMCPServer:
    """MCP server exposing eligibility checking tools."""

    def __init__(self):
        self.tools = {
            CheckEligibilityTool.name: CheckEligibilityTool(),
            BulkEligibilityTool.name: BulkEligibilityTool(),
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
