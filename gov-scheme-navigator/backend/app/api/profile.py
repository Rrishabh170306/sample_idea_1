from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    state: str | None = None
    district: str | None = None
    occupation: str | None = None
    income: float | None = None
    land_ownership: bool | None = None
    land_hectares: float | None = None
    categories: list[str] = Field(default_factory=list)


@router.get("/me")
async def read_profile() -> dict[str, object]:
    return {"profile": {}}


@router.put("/me")
async def update_profile(payload: ProfileUpdate) -> dict[str, object]:
    return {"updated": payload.model_dump()}
