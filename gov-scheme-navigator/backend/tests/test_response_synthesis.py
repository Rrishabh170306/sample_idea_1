import json

from app.agents.orchestrator import Orchestrator
from app.core.config import get_settings


def test_orchestrator_response_references_retrieved_scheme_entities(tmp_path, monkeypatch) -> None:
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "default-user": {
                    "state": "Central",
                    "occupation": "farmers",
                    "background": "rural",
                    "income": 200000,
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PROFILE_STORE_PATH", str(profile_path))
    get_settings.cache_clear()

    result = Orchestrator().run(
        {
            "query": "What schemes are available for farmers?",
        }
    )

    response = result["response"]
    scheme_names = {item["metadata"]["scheme_name"] for item in result["retrieved_chunks"]}

    assert scheme_names
    assert any(name in response for name in scheme_names)
    assert "Here is the information we found" not in response
    assert "Based on your query" not in response
    assert "Mock" not in response
    assert "farmers" in response
    assert "Central" in response

    get_settings.cache_clear()
