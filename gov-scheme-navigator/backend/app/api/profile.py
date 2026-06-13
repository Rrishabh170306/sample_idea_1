from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import AuthenticatedIdentity, get_authenticated_identity
from app.core.config import get_settings
from app.profile_identity import profile_key_from_user_id
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


def _profile_key(user_id: str) -> str:
    return profile_key_from_user_id(user_id)


@router.get("/me")
async def read_profile(identity: AuthenticatedIdentity = Depends(get_authenticated_identity)) -> ProfileResponse:
    profile = profile_store.get_profile(_profile_key(identity.user_id))

    return ProfileResponse(
        profile=ProfilePayload(**profile) if profile else None,
        identity=ProfileIdentity(email=identity.email, user_id=identity.user_id),
    )


@router.put("/me")
async def update_profile(
    payload: ProfilePayload,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> ProfileResponse:
    saved_profile = profile_store.upsert_profile(_profile_key(identity.user_id), payload.model_dump())

    return ProfileResponse(
        profile=ProfilePayload(**saved_profile),
        identity=ProfileIdentity(email=identity.email, user_id=identity.user_id),
    )
