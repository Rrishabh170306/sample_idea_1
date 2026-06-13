from __future__ import annotations

from app.agents.state import AgentState
from app.eligibility.engine import EligibilityEngine
from app.eligibility.rules import get_all_rule_sets, get_rule_set
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
                    results[scheme_id] = self._evaluate_rules(profile, rules)
                else:
                    logger.info("No rules found for scheme %s", scheme_id)
            else:
                for registered_scheme_id, rules in get_all_rule_sets().items():
                    results[registered_scheme_id] = self._evaluate_rules(profile, rules)
        except Exception as exc:
            logger.exception("Eligibility evaluation failed: %s", exc)

        return {"eligibility_results": results}

    def _evaluate_rules(self, profile: dict, rules: dict) -> dict:
        res = self.engine.evaluate(
            profile,
            {"rules": rules} if not isinstance(rules, dict) or "rules" not in rules else rules,
        )
        return {
            "eligible": res.eligible,
            "score": res.score,
            "gaps": res.gaps,
            "explanation": res.explanation,
        }
