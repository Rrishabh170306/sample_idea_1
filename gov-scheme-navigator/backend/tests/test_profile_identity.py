import json

from fastapi.testclient import TestClient

import app.api.profile as profile_api
from app.core.config import get_settings
from app.main import app
from app.profile_identity import profile_key_from_user_id, user_id_from_email
from app.profile_store import FileProfileStore
from tests.auth_helpers import signed_auth_headers


def test_profile_endpoint_uses_verified_identity_and_ignores_spoof_header(tmp_path, monkeypatch) -> None:
    verified_email = "verified@example.com"
    spoofed_email = "spoof@example.com"
    verified_user_id = user_id_from_email(verified_email)
    spoofed_user_id = user_id_from_email(spoofed_email)
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                profile_key_from_user_id(verified_user_id): {
                    "full_name": "Verified User",
                    "city": "Pune",
                },
                profile_key_from_user_id(spoofed_user_id): {
                    "full_name": "Spoofed User",
                    "city": "Delhi",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("AUTH_BACKEND_SHARED_SECRET", "test-secret")
    monkeypatch.setenv("PROFILE_STORE_PATH", str(profile_path))
    profile_api.profile_store = FileProfileStore(profile_path)
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.get(
        "/api/v1/profile/me",
        headers={**signed_auth_headers(verified_email), "X-User-Email": spoofed_email},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["identity"]["email"] == verified_email
    assert payload["identity"]["user_id"] == verified_user_id
    assert payload["profile"]["full_name"] == "Verified User"

    get_settings.cache_clear()


def test_profile_endpoint_rejects_unverified_email_header(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_BACKEND_SHARED_SECRET", "test-secret")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.get("/api/v1/profile/me", headers={"X-User-Email": "spoof@example.com"})

    assert response.status_code == 401

    get_settings.cache_clear()


def test_profile_endpoint_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_BACKEND_SHARED_SECRET", "test-secret")
    get_settings.cache_clear()

    headers = signed_auth_headers("user@example.com")
    headers["X-Auth-Signature"] = "invalid-signature"

    client = TestClient(app)
    response = client.get("/api/v1/profile/me", headers=headers)

    assert response.status_code == 401

    get_settings.cache_clear()
