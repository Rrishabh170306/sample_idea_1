from __future__ import annotations

from typing import Any


PM_KISAN_RULESET: dict[str, Any] = {
    "scheme_id": "PM-KISAN-001",
    "rules": {
        "and": [
            {">=": [{"var": "age"}, 18]},
            {"==": [{"var": "land_ownership"}, True]},
            {"<=": [{"var": "land_hectares"}, 2]},
            {"!": {"in": [{"var": "occupation"}, ["government_employee"]]}},
            {"==": [{"var": "income_tax_payer"}, False]},
        ]
    },
}

DEFAULT_RULESETS: dict[str, dict[str, Any]] = {PM_KISAN_RULESET["scheme_id"]: PM_KISAN_RULESET["rules"]}


def get_rule_set(scheme_id: str) -> dict[str, Any] | None:
    return DEFAULT_RULESETS.get(scheme_id)


def get_all_rule_sets() -> dict[str, dict[str, Any]]:
    return dict(DEFAULT_RULESETS)
