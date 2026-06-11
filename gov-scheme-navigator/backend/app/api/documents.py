from __future__ import annotations

from fastapi import APIRouter, File, UploadFile


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
async def list_documents() -> dict[str, list[dict[str, str]]]:
    return {"items": []}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, str]:
    return {"filename": file.filename or "document", "status": "queued"}
