from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EligibilityResult:
    eligible: bool
    score: float
    gaps: list[str] = field(default_factory=list)
    explanation: str = ""


class EligibilityEngine:
    def evaluate(self, user_profile: dict[str, Any], scheme_rules: dict[str, Any]) -> EligibilityResult:
        rules = scheme_rules.get("rules", scheme_rules)
        eligible = bool(self._evaluate_rule(rules, user_profile))
        gaps = self._collect_gaps(rules, user_profile)
        score = self._score(rules, gaps)
        explanation = self._build_explanation(eligible, gaps)
        return EligibilityResult(eligible=eligible, score=score, gaps=gaps, explanation=explanation)

    def _evaluate_rule(self, rule: Any, profile: dict[str, Any]) -> bool:
        if isinstance(rule, bool):
            return rule
        if isinstance(rule, (int, float, str)):
            return bool(rule)
        if isinstance(rule, list):
            return all(self._evaluate_rule(item, profile) for item in rule)
        if not isinstance(rule, dict) or not rule:
            return False

        if "var" in rule and len(rule) == 1:
            return self._lookup(profile, self._resolve_var_path(rule["var"])) is not None

        operator, operands = next(iter(rule.items()))
        values = self._resolve_operands(operands, profile)

        if operator == "and":
            return all(self._evaluate_rule(item, profile) for item in values)
        if operator == "or":
            return any(self._evaluate_rule(item, profile) for item in values)
        if operator == "!":
            return not self._evaluate_rule(operands, profile)
        if operator == "in" and len(values) == 2:
            left, right = values
            try:
                return left in right
            except TypeError:
                return False
        if operator == "==" and len(values) == 2:
            return values[0] == values[1]
        if operator == "!=" and len(values) == 2:
            return values[0] != values[1]
        if operator == ">" and len(values) == 2:
            return values[0] > values[1]
        if operator == ">=" and len(values) == 2:
            return values[0] >= values[1]
        if operator == "<" and len(values) == 2:
            return values[0] < values[1]
        if operator == "<=" and len(values) == 2:
            return values[0] <= values[1]
        return False

    def _collect_gaps(self, rule: Any, profile: dict[str, Any]) -> list[str]:
        if not isinstance(rule, dict):
            return [] if self._evaluate_rule(rule, profile) else ["One or more eligibility checks failed."]

        if "and" in rule:
            gaps: list[str] = []
            for clause in rule["and"]:
                if not self._evaluate_rule(clause, profile):
                    gaps.append(self._describe_clause(clause))
            return gaps

        return [] if self._evaluate_rule(rule, profile) else [self._describe_clause(rule)]

    def _score(self, rule: Any, gaps: list[str]) -> float:
        if isinstance(rule, dict) and "and" in rule:
            total = max(len(rule["and"]), 1)
            return max(0.0, 1.0 - (len(gaps) / total))
        return 1.0 if not gaps else 0.0

    def _build_explanation(self, eligible: bool, gaps: list[str]) -> str:
        if eligible:
            return "You satisfy the available eligibility rules."
        if not gaps:
            return "One or more eligibility conditions were not met."
        return " ".join(gaps)

    def _resolve_operands(self, operands: Any, profile: dict[str, Any]) -> list[Any]:
        if isinstance(operands, list):
            return [self._resolve_value(operand, profile) for operand in operands]
        return [self._resolve_value(operands, profile)]

    def _resolve_value(self, operand: Any, profile: dict[str, Any]) -> Any:
        if isinstance(operand, dict) and "var" in operand:
            default = operand.get("default")
            value = self._lookup(profile, self._resolve_var_path(operand["var"]))
            return default if value is None else value
        if isinstance(operand, list):
            return [self._resolve_value(item, profile) for item in operand]
        return operand

    def _resolve_var_path(self, path: Any) -> str:
        if isinstance(path, list):
            return str(path[0])
        return str(path)

    def _lookup(self, profile: dict[str, Any], path: str) -> Any:
        current: Any = profile
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _describe_clause(self, clause: Any) -> str:
        if not isinstance(clause, dict) or not clause:
            return "An eligibility condition was not met."

        operator, operands = next(iter(clause.items()))
        if operator in {"<", "<=", ">", ">=", "==", "!="} and isinstance(operands, list) and len(operands) == 2:
            left = self._describe_operand(operands[0])
            right = self._describe_operand(operands[1])
            return f"{left} must satisfy {operator} {right}."
        if operator == "in" and isinstance(operands, list) and len(operands) == 2:
            left = self._describe_operand(operands[0])
            right = self._describe_operand(operands[1])
            return f"{left} must be in {right}."
        if operator == "!":
            return f"Condition must not hold: {self._describe_operand(operands)}."
        if operator in {"and", "or"}:
            return "One of the grouped eligibility conditions was not met."
        if operator == "var":
            return f"Missing required field: {self._describe_operand(operands)}."
        return "An eligibility condition was not met."

    def _describe_operand(self, operand: Any) -> str:
        if isinstance(operand, dict) and "var" in operand:
            return str(operand["var"])
        if isinstance(operand, list):
            return ", ".join(self._describe_operand(item) for item in operand)
        return repr(operand)


def evaluate_eligibility(user_profile: dict[str, Any], scheme_rules: dict[str, Any]) -> EligibilityResult:
    return EligibilityEngine().evaluate(user_profile, scheme_rules)
