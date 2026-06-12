from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlparse


def _parse_redis_url(value: str) -> tuple[str, int, int]:
    try:
        parsed = urlparse(value)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        db = int((parsed.path or "").lstrip('/') or 0)
        return host, port, db
    except Exception:
        return "localhost", 6379, 0


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    app_name: str = "AI Government Scheme Navigator"
    version: str = "0.1.0"
    environment: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    api_prefix: str = field(default_factory=lambda: os.getenv("API_PREFIX", "/api/v1"))
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
        ) or ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    # Database URL should be provided via environment variable; keep empty if unset
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "")
    )
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    # Convenience parsed fields for code that expects host/port/db
    redis_host: str = field(default_factory=lambda: _parse_redis_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))[0])
    redis_port: int = field(default_factory=lambda: _parse_redis_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))[1])
    redis_db: int = field(default_factory=lambda: _parse_redis_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))[2])
    rate_limit: str = field(default_factory=lambda: os.getenv("RATE_LIMIT", "100/minute"))
    # Generic LLM configuration (supports Gemini, Claude, or self-hosted endpoints)
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", os.getenv("LLM", "gemini")))
    llm_api_key: str | None = field(
        default_factory=lambda: os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("CLAUDE_API_KEY")
    )
    llm_api_url: str | None = field(default_factory=lambda: os.getenv("LLM_API_URL", None))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "openai/gpt-5"))
    profile_store_path: str = field(
        default_factory=lambda: os.getenv("PROFILE_STORE_PATH", "data/profiles.json")
    )
    # If >0 the scraper runner will repeat every N seconds; 0 (default) runs once
    scrape_interval_seconds: int = field(default_factory=lambda: int(os.getenv("SCRAPE_INTERVAL_SECONDS", "0") or 0))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Export a singleton `settings` for backwards compatibility across the codebase
settings = get_settings()
