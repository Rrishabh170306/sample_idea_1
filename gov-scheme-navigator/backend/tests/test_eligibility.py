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
