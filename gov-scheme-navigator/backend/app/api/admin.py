from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/review_queue")
async def get_review_queue() -> list[dict[str, Any]]:
    """Fetch pending items from the Human-in-the-Loop review queue."""
    # This is a stub returning a mock queue. In reality, it would call db.query(ReviewQueue).filter_by(status="pending")
    return [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "session_id": "session-1",
            "query": "Aadhaar card upload",
            "confidence": 0.5,
            "reason": "Low confidence (0.5) extracting Aadhaar",
            "status": "pending"
        }
    ]

@router.post("/review/{item_id}/resolve")
async def resolve_review_item(item_id: str, action: str) -> dict[str, str]:
    """
    Resolve a pending queue item. Action must be 'approve' or 'reject'.
    """
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")
        
    # Logic to update ReviewQueue status and potentially trigger state updates
    return {"status": f"Item {item_id} resolved with action {action}."}
