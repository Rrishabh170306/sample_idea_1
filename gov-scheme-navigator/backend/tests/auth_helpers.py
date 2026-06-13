import time


def signed_auth_headers(email: str, secret: str = "test-secret") -> dict[str, str]:
    from app.core.auth import sign_identity
    from app.profile_identity import normalize_email

    normalized_email = normalize_email(email)
    timestamp = str(int(time.time()))
    return {
        "X-Auth-User-Email": normalized_email,
        "X-Auth-Timestamp": timestamp,
        "X-Auth-Signature": sign_identity(normalized_email, timestamp, secret),
    }
