from __future__ import annotations
from typing import Any
from app.agents.state import AgentState

class ProfileAgent:
    def __init__(self, profile_crud=None):
        self.crud = profile_crud
        
    def load_profile(self, state: AgentState) -> dict:
        user_id = state.get("user_profile", {}).get("user_id", "default-user")
        
        if self.crud:
            profile_model = self.crud.get_profile(user_id)
            if profile_model:
                # Convert to dict
                user_profile = {col.name: getattr(profile_model, col.name) for col in profile_model.__table__.columns}
            else:
                user_profile = {"user_id": user_id, "age": 30, "occupation": "unknown"}
        else:
            user_profile = state.get("user_profile", {})
            if not user_profile:
                user_profile = {
                    "user_id": user_id,
                    "age": 30,
                    "state": "unknown",
                    "occupation": "unknown"
                }
        return {"user_profile": user_profile}

    def update_profile(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        if self.crud:
            self.crud.create_or_update_profile(user_id, updates)
        return updates
