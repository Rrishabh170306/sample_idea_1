from __future__ import annotations

from app.agents.state import AgentState
from app.eligibility.engine import EligibilityEngine
from app.eligibility.rules import get_rule_set
import logging

logger = logging.getLogger(__name__)


class EligibilityAgent:
    def __init__(self):
        self.engine = EligibilityEngine()

    def evaluate(self, state: AgentState) -> dict:
        profile = state.get("user_profile", {}) or {}

        # If a specific scheme_id is requested in state, evaluate that first
        scheme_id = state.get("scheme_id")
        results = {}

        try:
            if scheme_id:
                rules = get_rule_set(scheme_id)
                if rules:
                    res = self.engine.evaluate(profile, {"rules": rules} if not isinstance(rules, dict) or "rules" not in rules else rules)
                    results[scheme_id] = {
                        "eligible": res.eligible,
                        "score": res.score,
                        "gaps": res.gaps,
                        "explanation": res.explanation,
                    }
                else:
                    logger.info("No rules found for scheme %s", scheme_id)
            else:
                # In absence of explicit scheme_id, fall back to a lightweight local check
                mock_scheme_rules = {
                    "scheme_id": "MOCK-001",
                    "rules": {"and": [{">=": [{"var": "age"}, 18]}]}
                }
                res = self.engine.evaluate(profile, mock_scheme_rules)
                results[mock_scheme_rules["scheme_id"]] = {
                    "eligible": res.eligible,
                    "score": res.score,
                    "gaps": res.gaps,
                    "explanation": res.explanation,
                }
        except Exception as exc:
            logger.exception("Eligibility evaluation failed: %s", exc)

        return {"eligibility_results": results}
