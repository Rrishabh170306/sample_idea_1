from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Lazily instantiate the Orchestrator so startup errors don't crash import
_orchestrator = None


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        try:
            from app.agents.orchestrator import Orchestrator
            _orchestrator = Orchestrator()
            logger.info("Orchestrator initialised on first chat request")
        except Exception as exc:
            logger.exception("Failed to initialise Orchestrator: %s", exc)
            raise HTTPException(status_code=503, detail="Agent system unavailable") from exc
    return _orchestrator


class ChatMessage(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str | None = None
    user_profile: dict[str, Any] | None = None


class SchemeResult(BaseModel):
    scheme_id: str
    name: str
    source: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = {}


class EligibilityInfo(BaseModel):
    eligible: bool
    score: float
    explanation: str
    gaps: list[dict[str, Any]] = []


class ChatReply(BaseModel):
    reply: str
    session_id: str
    user_email: str | None = None
    schemes: list[SchemeResult] = []
    eligibility: dict[str, EligibilityInfo] = {}
    citations: list[dict[str, Any]] = []
    query_type: str = "general"


@router.post("/messages", response_model=ChatReply)
async def create_message(
    payload: ChatMessage,
    x_user_email: str | None = Header(default=None),
) -> ChatReply:
    """Process a user message through the full agent pipeline.

    Returns a structured reply with matched schemes, eligibility results,
    and source citations.
    """
    user_email = x_user_email.strip().lower() if x_user_email else None
    session_id = payload.session_id or str(uuid.uuid4())
    user_id = payload.user_id or (
        user_email.replace("@", "_").replace(".", "_") if user_email else "anonymous"
    )

    orchestrator = _get_orchestrator()

    # Build AgentState
    from app.agents.state import AgentState
    initial_state: AgentState = {
        "query": payload.message,
        "session_id": session_id,
        "user_id": user_id,
        "user_profile": payload.user_profile or {},
        "query_type": "general",
        "retrieved_chunks": [],
        "graph_results": [],
        "eligibility_results": {},
        "citations": [],
        "response": "",
        "needs_human_review": False,
        "error": None,
    }

    try:
        final_state = await orchestrator.arun(initial_state)
    except Exception as exc:
        logger.exception("Orchestrator failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    reply_text = final_state.get("response") or "I could not find relevant schemes for your query."

    # Build scheme results from graph_results + retrieved_chunks
    schemes: list[SchemeResult] = []
    seen: set[str] = set()

    for r in (final_state.get("graph_results") or []):
        name = str(r.get("name", ""))
        sid = str(r.get("scheme_id", ""))
        key = sid or name.lower()
        if name and key not in seen:
            schemes.append(SchemeResult(
                scheme_id=sid,
                name=name,
                source=str(r.get("source", "graph")),
                score=float(r.get("relevance_score", r.get("score", 0.0))),
                metadata=r.get("metadata", {}),
            ))
            seen.add(key)

    for chunk in (final_state.get("retrieved_chunks") or []):
        meta = chunk.get("metadata", {}) or {}
        name = str(meta.get("scheme_name", ""))
        sid = str(meta.get("id", ""))
        if not name and str(chunk.get("content", "")).lower().startswith("scheme:"):
            name = chunk["content"].split(":", 1)[1].strip()
        key = sid or name.lower()
        if name and key not in seen:
            schemes.append(SchemeResult(
                scheme_id=sid,
                name=name,
                source=str(meta.get("source", "rag")),
                score=float(chunk.get("score", 0.0)),
                metadata=meta,
            ))
            seen.add(key)

    # Eligibility results
    eligibility_out: dict[str, EligibilityInfo] = {}
    for scheme_id, res in (final_state.get("eligibility_results") or {}).items():
        eligibility_out[scheme_id] = EligibilityInfo(
            eligible=bool(res.get("eligible", False)),
            score=float(res.get("score", 0.0)),
            explanation=str(res.get("explanation", "")),
            gaps=list(res.get("gaps", [])),
        )

    return ChatReply(
        reply=reply_text,
        session_id=session_id,
        user_email=user_email,
        schemes=schemes,
        eligibility=eligibility_out,
        citations=final_state.get("citations") or [],
        query_type=final_state.get("query_type", "general"),
    )


@router.websocket("/ws")
async def chat_socket(websocket: WebSocket) -> None:
    """WebSocket chat — streams token-by-token responses."""
    await websocket.accept()
    await websocket.send_json({"status": "connected"})
    session_id = str(uuid.uuid4())

    try:
        orchestrator = _get_orchestrator()
    except HTTPException:
        await websocket.send_json({"error": "Agent system unavailable"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            user_profile = data.get("user_profile", {})

            if not message:
                continue

            from app.agents.state import AgentState
            initial_state: AgentState = {
                "query": message,
                "session_id": session_id,
                "user_id": data.get("user_id", "ws_user"),
                "user_profile": user_profile,
                "query_type": "general",
                "retrieved_chunks": [],
                "graph_results": [],
                "eligibility_results": {},
                "citations": [],
                "response": "",
                "needs_human_review": False,
                "error": None,
            }
            try:
                final_state = await orchestrator.arun(initial_state)
                await websocket.send_json({
                    "reply": final_state.get("response", ""),
                    "session_id": session_id,
                    "query_type": final_state.get("query_type", "general"),
                    "schemes": [
                        {"name": r.get("name", ""), "scheme_id": r.get("scheme_id", "")}
                        for r in (final_state.get("graph_results") or [])[:5]
                    ],
                    "citations": final_state.get("citations") or [],
                })
            except Exception as exc:
                logger.exception("WS orchestrator error: %s", exc)
                await websocket.send_json({"error": str(exc)})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected (session=%s)", session_id)
