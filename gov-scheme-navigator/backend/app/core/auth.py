from __future__ import annotations

import hmac
import time
from dataclasses import dataclass
from hashlib import sha256

from fastapi import Header, HTTPException

from app.core.config import get_settings
from app.profile_identity import normalize_email, user_id_from_email


AUTH_SIGNATURE_TTL_SECONDS = 300


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    email: str
    user_id: str


def sign_identity(email: str, timestamp: str, secret: str) -> str:
    normalized_email = normalize_email(email)
    payload = f"{timestamp}.{normalized_email}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()


def verify_identity_signature(email: str, timestamp: str, signature: str, secret: str) -> bool:
    expected = sign_identity(email, timestamp, secret)
    return hmac.compare_digest(expected, signature)


async def get_authenticated_identity(
    x_auth_user_email: str | None = Header(default=None),
    x_auth_timestamp: str | None = Header(default=None),
    x_auth_signature: str | None = Header(default=None),
) -> AuthenticatedIdentity:
    settings = get_settings()
    if not settings.backend_auth_secret:
        raise HTTPException(status_code=500, detail="Backend auth secret is not configured.")

    if not x_auth_user_email or not x_auth_timestamp or not x_auth_signature:
        raise HTTPException(status_code=401, detail="Missing verified authentication headers.")

    try:
        issued_at = int(x_auth_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication timestamp.") from exc

    if abs(int(time.time()) - issued_at) > AUTH_SIGNATURE_TTL_SECONDS:
        raise HTTPException(status_code=401, detail="Expired authentication signature.")

    email = normalize_email(x_auth_user_email)
    if not email or not verify_identity_signature(email, x_auth_timestamp, x_auth_signature, settings.backend_auth_secret):
        raise HTTPException(status_code=401, detail="Invalid authentication signature.")

    return AuthenticatedIdentity(email=email, user_id=user_id_from_email(email))
