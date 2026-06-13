import json

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.profile_identity import profile_key_from_user_id, user_id_from_email
from tests.auth_helpers import signed_auth_headers


def test_chat_endpoint_preserves_echo_contract_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CHAT_USE_ORCHESTRATOR", raising=False)
    monkeypatch.setenv("AUTH_BACKEND_SHARED_SECRET", "test-secret")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat/messages",
        json={"message": "hello", "session_id": "session-1"},
        headers=signed_auth_headers("USER@example.com"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Received: hello",
        "session_id": "session-1",
        "user_email": "user@example.com",
    }

    get_settings.cache_clear()


def test_chat_endpoint_uses_orchestrator_when_enabled(tmp_path, monkeypatch) -> None:
    email = "farmer@example.com"
    user_id = user_id_from_email(email)
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                profile_key_from_user_id(user_id): {
                    "state": "Central",
                    "occupation": "farmers",
                    "background": "rural",
                    "income": 200000,
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("CHAT_USE_ORCHESTRATOR", "true")
    monkeypatch.setenv("PROFILE_STORE_PATH", str(profile_path))
    monkeypatch.setenv("AUTH_BACKEND_SHARED_SECRET", "test-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat/messages",
        json={"message": "What schemes are available for farmers?", "session_id": "session-2"},
        headers={**signed_auth_headers(email), "X-User-Email": "spoof@example.com"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["session_id"] == "session-2"
    assert payload["user_email"] == email
    assert "Received:" not in payload["reply"]
    assert "PM-KISAN Samman Nidhi" in payload["reply"] or "Kisan Credit Card" in payload["reply"]

    get_settings.cache_clear()


def test_chat_endpoint_rejects_unverified_spoofed_email_header(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_BACKEND_SHARED_SECRET", "test-secret")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat/messages",
        json={"message": "hello"},
        headers={"X-User-Email": "spoof@example.com"},
    )

    assert response.status_code == 401

    get_settings.cache_clear()


def test_chat_endpoint_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_BACKEND_SHARED_SECRET", "test-secret")
    get_settings.cache_clear()

    headers = signed_auth_headers("user@example.com")
    headers["X-Auth-Signature"] = "invalid-signature"

    client = TestClient(app)
    response = client.post(
        "/api/v1/chat/messages",
        json={"message": "hello"},
        headers=headers,
    )

    assert response.status_code == 401

    get_settings.cache_clear()
