from __future__ import annotations

from typing import Any


class ProfileAgent:
    def load_profile(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("Profile loading will be implemented here.")

    def update_profile(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Profile updates will be implemented here.")
