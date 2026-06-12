import json

from app.agents.orchestrator import Orchestrator
from app.core.config import get_settings
from app.profile_identity import profile_key_from_user_id, user_id_from_email


def test_orchestrator_uses_real_wired_dependencies(tmp_path, monkeypatch) -> None:
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "default-user": {
                    "state": "Central",
                    "occupation": "farmers",
                    "full_name": "Farmer User",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PROFILE_STORE_PATH", str(profile_path))
    get_settings.cache_clear()

    orchestrator = Orchestrator()
    result = orchestrator.run(
        {
            "query": "What schemes are available for farmers?",
            "user_profile": {
                "income": 200000,
                "background": "rural",
            },
        }
    )

    assert result["response"]
    assert result["retrieved_chunks"]
    assert result["retrieved_chunks"][0]["content"] != "Mock retrieved content for query: What schemes are available for farmers?"
    assert result["graph_results"]
    assert result["graph_results"][0].get("name")
    assert result["graph_results"][0].get("name") != "Mock Graph Node"
    assert result["user_profile"]["occupation"] == "farmers"
    assert result["user_profile"]["state"] == "Central"
    assert result["user_profile"]["income"] == 200000

    get_settings.cache_clear()


def test_orchestrator_loads_profile_saved_by_profile_api_key(tmp_path, monkeypatch) -> None:
    profile_path = tmp_path / "profiles.json"
    email = "farmer@example.com"
    user_id = user_id_from_email(email)
    profile_path.write_text(
        json.dumps(
            {
                profile_key_from_user_id(user_id): {
                    "state": "Central",
                    "occupation": "farmers",
                    "full_name": "Saved Farmer",
                    "income": 150000,
                    "background": "rural",
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("PROFILE_STORE_PATH", str(profile_path))
    get_settings.cache_clear()

    result = Orchestrator().run(
        {
            "query": "What schemes are available for farmers?",
            "user_profile": {
                "user_email": email,
            },
        }
    )

    assert result["user_profile"]["user_id"] == user_id
    assert result["user_profile"]["email"] == email
    assert result["user_profile"]["full_name"] == "Saved Farmer"
    assert result["user_profile"]["occupation"] == "farmers"
    assert result["user_profile"]["state"] == "Central"
    assert result["retrieved_chunks"]
    assert result["graph_results"]

    get_settings.cache_clear()
