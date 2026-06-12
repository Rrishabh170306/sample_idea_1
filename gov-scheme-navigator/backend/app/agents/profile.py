from __future__ import annotations
from typing import Any
from app.agents.state import AgentState
from app.profile_identity import normalize_email, user_id_from_email

class ProfileAgent:
    def __init__(self, profile_crud=None):
        self.crud = profile_crud
        
    def load_profile(self, state: AgentState) -> dict:
        incoming_profile = state.get("user_profile", {}) or {}
        user_email = incoming_profile.get("email") or incoming_profile.get("user_email") or state.get("user_email")
        user_id = incoming_profile.get("user_id")
        if not user_id and user_email:
            user_id = user_id_from_email(str(user_email))
        user_id = user_id or "default-user"
        stored_profile: dict[str, Any] = {}

        if self.crud:
            profile_model = self.crud.get_profile(user_id)
            if profile_model:
                if isinstance(profile_model, dict):
                    stored_profile = dict(profile_model)
                elif hasattr(profile_model, "__table__"):
                    stored_profile = {col.name: getattr(profile_model, col.name) for col in profile_model.__table__.columns}

        normalized_email = normalize_email(str(user_email)) if user_email else None
        user_profile = {"user_id": user_id, **stored_profile, **incoming_profile}
        if normalized_email:
            user_profile["email"] = normalized_email
        return {"user_profile": user_profile}

    def update_profile(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        if self.crud:
            self.crud.create_or_update_profile(user_id, updates)
        return updates
