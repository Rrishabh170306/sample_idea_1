from __future__ import annotations

from typing import Any


class EligibilityAgent:
    def evaluate(self, profile: dict[str, Any], rule_set: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Eligibility execution will be implemented here.")
