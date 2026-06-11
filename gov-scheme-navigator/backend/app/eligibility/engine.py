from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

try:
    from json_logic import jsonLogic
except Exception:  # pragma: no cover - dependency handling
    try:
        # Local vendored evaluator
        from .json_logic import jsonLogic
    except Exception:
        def jsonLogic(rules, data):
            logger.warning("json_logic package not available; jsonLogic calls will return False.")
            return False


@dataclass(slots=True)
class EligibilityResult:
    eligible: bool
    score: float
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""


class EligibilityEngine:
    def evaluate(self, user_profile: Dict[str, Any], scheme_rules: Dict[str, Any]) -> EligibilityResult:
        rules = scheme_rules.get("rules", scheme_rules)

        # Primary evaluation
        try:
            is_eligible = bool(jsonLogic(rules, user_profile))
        except Exception as exc:
            logger.exception("Error evaluating JSONLogic: %s", exc)
            is_eligible = False

        # Gap analysis
        gaps: List[Dict[str, Any]] = []
        atomic_checks = []

        if isinstance(rules, dict) and "and" in rules:
            atomic_checks = list(rules["and"])
        else:
            atomic_checks = [rules]

        for rule in atomic_checks:
            try:
                passed = bool(jsonLogic(rule, user_profile))
            except Exception:
                passed = False

            if not passed:
                gaps.append(self._explain_gap(rule, user_profile))

        # Score: proportion of passing atomic checks
        total = len(atomic_checks) if atomic_checks else 1
        passed_count = total - len(gaps)
        score = float(passed_count) / float(total)

        # Explanation
        if is_eligible:
            explanation = "You satisfy the available eligibility rules."
        else:
            if gaps:
                explanation = " ".join(g.get("gap", "") for g in gaps)
            else:
                explanation = "One or more eligibility conditions were not met."

        return EligibilityResult(
            eligible=is_eligible,
            score=max(0.0, min(1.0, score)),
            gaps=gaps,
            explanation=explanation,
        )

    def _explain_gap(self, rule: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a human-friendly gap explanation for a single JSONLogic rule."""
        if not isinstance(rule, dict) or not rule:
            return {"field": "unknown", "user_value": None, "required": None, "gap": "An eligibility condition was not met."}

        operator = next(iter(rule.keys()))
        operands = rule[operator]

        if not isinstance(operands, list):
            return {"field": "unknown", "user_value": None, "required": None, "gap": f"Condition failed for operator {operator}."}

        field_name = "unknown"
        user_value = None
        required_value = None

        # Extract field name and required value
        if len(operands) >= 1 and isinstance(operands[0], dict) and "var" in operands[0]:
            field_name = operands[0]["var"]
            user_value = profile.get(field_name)

        if len(operands) >= 2:
            required_value = operands[1]

        gap_msg = ""
        try:
            if operator == "<=":
                if isinstance(user_value, (int, float)) and isinstance(required_value, (int, float)):
                    diff = round(user_value - required_value, 3)
                    gap_msg = f"Your {field_name} ({user_value}) exceeds the limit by {diff}."
                else:
                    gap_msg = f"Your {field_name} ({user_value}) must be <= {required_value}."
            elif operator == ">=":
                if isinstance(user_value, (int, float)) and isinstance(required_value, (int, float)):
                    diff = round(required_value - user_value, 3)
                    gap_msg = f"Your {field_name} ({user_value}) is below the minimum by {diff}."
                else:
                    gap_msg = f"Your {field_name} ({user_value}) must be >= {required_value}."
            elif operator == "==":
                gap_msg = f"Your {field_name} must be exactly {required_value}."
            elif operator == "in":
                gap_msg = f"Your {field_name} ({user_value}) is not an accepted value ({required_value})."
            elif operator == "!":
                # Negation: usually wraps another operator
                gap_msg = "A restricted condition was detected."
                if isinstance(operands[0], dict):
                    inner = operands[0]
                    inner_op = next(iter(inner.keys()))
                    inner_operands = inner.get(inner_op)
                    if inner_op == "in" and isinstance(inner_operands, list) and len(inner_operands) == 2:
                        fn = inner_operands[0].get("var") if isinstance(inner_operands[0], dict) else None
                        uv = profile.get(fn) if fn else None
                        gap_msg = f"Your {fn} ({uv}) is restricted from this scheme."
            else:
                gap_msg = f"Condition {operator} failed for {field_name}."
        except Exception:
            gap_msg = f"Condition {operator} failed for {field_name}."

        return {"field": field_name, "user_value": user_value, "required": required_value, "gap": gap_msg}


def evaluate_eligibility(user_profile: Dict[str, Any], scheme_rules: Dict[str, Any]) -> EligibilityResult:
    return EligibilityEngine().evaluate(user_profile, scheme_rules)
