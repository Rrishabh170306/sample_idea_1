from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class FileProfileStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def get_profile(self, user_key: str) -> dict[str, Any] | None:
        payload = self._read()
        profile = payload.get(user_key)
        return profile if isinstance(profile, dict) else None

    def upsert_profile(self, user_key: str, profile: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            payload[user_key] = profile
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return profile

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return {}

        if not raw.strip():
            return {}

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}

        return payload if isinstance(payload, dict) else {}
