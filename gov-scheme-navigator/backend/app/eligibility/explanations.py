from __future__ import annotations

from app.eligibility.engine import EligibilityResult


def explain_eligibility(result: EligibilityResult) -> str:
    if result.eligible:
        return result.explanation or "You appear to satisfy the available eligibility rules."
    if result.gaps:
        return " ".join(result.gaps)
    return result.explanation or "Some eligibility conditions were not met."
