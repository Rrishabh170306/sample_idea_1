import json

from app.agents.eligibility_agent import EligibilityAgent
from app.agents.orchestrator import Orchestrator
from app.core.config import get_settings
from app.eligibility.engine import EligibilityEngine
from app.eligibility.rules import PM_KISAN_RULESET


def test_eligibility_engine_detects_gaps() -> None:
    engine = EligibilityEngine()
    profile = {
        "age": 17,
        "land_ownership": False,
        "land_hectares": 3,
        "occupation": "government_employee",
        "income_tax_payer": True,
    }

    result = engine.evaluate(profile, PM_KISAN_RULESET)

    assert not result.eligible
    assert result.gaps
    assert result.score < 1.0


def test_eligibility_agent_uses_registered_rules_without_default_mock() -> None:
    result = EligibilityAgent().evaluate(
        {
            "user_profile": {
                "age": 35,
                "land_ownership": True,
                "land_hectares": 1.5,
                "occupation": "farmer",
                "income_tax_payer": False,
            }
        }
    )

    eligibility = result["eligibility_results"]
    assert eligibility
    assert "PM-KISAN-001" in eligibility
    assert "MOCK-001" not in eligibility
    assert eligibility["PM-KISAN-001"]["eligible"] is True
    assert eligibility["PM-KISAN-001"]["score"] == 1.0


def test_orchestrator_eligibility_query_uses_profile_and_registered_rules(tmp_path, monkeypatch) -> None:
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "default-user": {
                    "state": "Central",
                    "occupation": "farmer",
                    "age": 35,
                    "land_ownership": True,
                    "land_hectares": 1.5,
                    "income_tax_payer": False,
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PROFILE_STORE_PATH", str(profile_path))
    get_settings.cache_clear()

    result = Orchestrator().run({"query": "Am I eligible for PM-KISAN?"})

    eligibility = result["eligibility_results"]
    assert result["query_type"] == "eligibility"
    assert eligibility
    assert "PM-KISAN-001" in eligibility
    assert "MOCK-001" not in eligibility
    assert eligibility["PM-KISAN-001"]["eligible"] is True
    assert result["response"]

    get_settings.cache_clear()
