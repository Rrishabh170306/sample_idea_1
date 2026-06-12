from __future__ import annotations

from fastapi import APIRouter, Header, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str
    session_id: str | None = None


class ChatReply(BaseModel):
    reply: str
    session_id: str | None = None
    user_email: str | None = None


@router.post("/messages")
async def create_message(payload: ChatMessage, x_user_email: str | None = Header(default=None)) -> ChatReply:
    user_email = x_user_email.strip().lower() if x_user_email else None
    return ChatReply(
        reply=f"Received: {payload.message}",
        session_id=payload.session_id,
        user_email=user_email,
    )


@router.websocket("/ws")
async def chat_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"status": "connected"})
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"Echo: {message}")
    except WebSocketDisconnect:
        return
