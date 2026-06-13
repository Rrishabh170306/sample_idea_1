from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass

from app.agents.orchestrator import Orchestrator
from app.core.config import get_settings
from app.profile_identity import normalize_email

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChatServiceResult:
    reply: str
    session_id: str | None
    user_email: str | None


class ChatService:
    def __init__(self, orchestrator: Orchestrator | None = None) -> None:
        self.orchestrator = orchestrator

    async def create_reply(
        self,
        message: str,
        session_id: str | None = None,
        user_email: str | None = None,
    ) -> ChatServiceResult:
        normalized_email = normalize_email(user_email) if user_email else None

        if not get_settings().chat_use_orchestrator:
            return ChatServiceResult(
                reply=f"Received: {message}",
                session_id=session_id,
                user_email=normalized_email,
            )

        try:
            result = await asyncio.to_thread(
                self._run_orchestrator,
                message,
                session_id,
                normalized_email,
            )
            reply = result.get("response") or "No response could be generated from the available scheme data."
        except Exception as exc:
            logger.exception("Chat orchestrator failed: %s", exc)
            reply = "I could not process this request with the scheme assistant right now."

        return ChatServiceResult(
            reply=reply,
            session_id=session_id,
            user_email=normalized_email,
        )

    def _run_orchestrator(
        self,
        message: str,
        session_id: str | None,
        normalized_email: str | None,
    ) -> dict:
        orchestrator = self.orchestrator or Orchestrator()
        state = {
            "query": message,
            "session_id": session_id,
            "user_profile": {},
        }
        if normalized_email:
            state["user_email"] = normalized_email
            state["user_profile"]["user_email"] = normalized_email

        return orchestrator.run(state)
