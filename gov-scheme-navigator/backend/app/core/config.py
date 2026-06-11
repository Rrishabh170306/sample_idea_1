from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    app_name: str = "AI Government Scheme Navigator"
    version: str = "0.1.0"
    environment: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    api_prefix: str = field(default_factory=lambda: os.getenv("API_PREFIX", "/api/v1"))
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ORIGINS", "*")) or ["*"]
    )
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://user:pass@localhost:5432/govschemes",
        )
    )
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    rate_limit: str = field(default_factory=lambda: os.getenv("RATE_LIMIT", "100/minute"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
