from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/schemes", tags=["schemes"])


class SchemeSearchRequest(BaseModel):
    query: str
    state: str | None = None
    categories: list[str] = Field(default_factory=list)
    limit: int = 10


@router.get("/")
async def list_schemes() -> dict[str, list[dict[str, str]]]:
    return {"items": []}


@router.post("/search")
async def search_schemes(payload: SchemeSearchRequest) -> dict[str, object]:
    return {"query": payload.query, "results": []}
