from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.auth import AuthenticatedIdentity, get_authenticated_identity
from app.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()


class ChatMessage(BaseModel):
    message: str
    session_id: str | None = None


class ChatReply(BaseModel):
    reply: str
    session_id: str | None = None
    user_email: str | None = None


@router.post("/messages")
async def create_message(
    payload: ChatMessage,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> ChatReply:
    result = await chat_service.create_reply(
        message=payload.message,
        session_id=payload.session_id,
        user_email=identity.email,
    )
    return ChatReply(
        reply=result.reply,
        session_id=result.session_id,
        user_email=result.user_email,
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
