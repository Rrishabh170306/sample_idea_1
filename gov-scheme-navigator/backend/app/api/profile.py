from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.profile_identity import normalize_email, profile_key_from_user_id, user_id_from_email
from app.profile_store import FileProfileStore


router = APIRouter(prefix="/profile", tags=["profile"])
settings = get_settings()
profile_store = FileProfileStore(settings.profile_store_path)


class ProfilePayload(BaseModel):
    full_name: str = ""
    dob: str | None = None
    address: str = ""
    city: str = ""
    pin_code: str = ""
    income: float | None = None
    background: str | None = None
    education_background: str = ""
    language: str = "English"
    voice_enabled: bool = False


class ProfileIdentity(BaseModel):
    email: str | None = None
    user_id: str | None = None


class ProfileResponse(BaseModel):
    profile: ProfilePayload | None = None
    identity: ProfileIdentity


def _resolve_identity(user_email: str | None) -> tuple[str, str]:
    if not user_email:
        raise HTTPException(status_code=401, detail="Missing X-User-Email header.")

    email = normalize_email(user_email)
    if not email:
        raise HTTPException(status_code=401, detail="Missing X-User-Email header.")

    user_id = user_id_from_email(email)
    return email, user_id


def _profile_key(user_id: str) -> str:
    return profile_key_from_user_id(user_id)


@router.get("/me")
async def read_profile(x_user_email: str | None = Header(default=None)) -> ProfileResponse:
    email, user_id = _resolve_identity(x_user_email)
    profile = profile_store.get_profile(_profile_key(user_id))

    return ProfileResponse(
        profile=ProfilePayload(**profile) if profile else None,
        identity=ProfileIdentity(email=email, user_id=user_id),
    )


@router.put("/me")
async def update_profile(payload: ProfilePayload, x_user_email: str | None = Header(default=None)) -> ProfileResponse:
    email, user_id = _resolve_identity(x_user_email)
    saved_profile = profile_store.upsert_profile(_profile_key(user_id), payload.model_dump())

    return ProfileResponse(
        profile=ProfilePayload(**saved_profile),
        identity=ProfileIdentity(email=email, user_id=user_id),
    )
