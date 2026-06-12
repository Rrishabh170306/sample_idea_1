from __future__ import annotations

from hashlib import sha256
from uuid import UUID, uuid5


PROFILE_NAMESPACE = UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def user_id_from_email(email: str) -> str:
    return str(uuid5(PROFILE_NAMESPACE, normalize_email(email)))


def profile_key_from_user_id(user_id: str) -> str:
    return sha256(user_id.encode("utf-8")).hexdigest()
