"""
Change detection and freshness monitoring for web scraping.
Improved: canonical URL keys, bytes-safe hashing, atomic Redis updates, and richer return types.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Union
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scheme
from app.core.config import settings

logger = logging.getLogger(__name__)


def _canonicalize_url(raw_url: str) -> str:
    """Normalize URLs for consistent Redis keys: strip fragments, sort query params, lowercase host."""
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    # Remove fragment
    query = urlencode(sorted(parse_qsl(parsed.query)))
    netloc = parsed.netloc.lower()
    normalized = urlunparse((parsed.scheme.lower(), netloc, parsed.path or "", "", query, ""))
    return normalized


@dataclass
class ChangeCheckResult:
    changed: bool
    old_hash: Optional[str]
    new_hash: str
    timestamp: datetime


class ChangeDetector:
    """Hash-based change detection with Redis caching.

    - Accepts `str` or `bytes` content.
    - Returns a `ChangeCheckResult` for richer information.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        try:
            # Prefer a full redis URL when available
            self.redis = redis_client or redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            # Fallback to host/port for legacy environments
            self.redis = redis_client or redis.Redis(
                host=getattr(settings, "redis_host", "localhost"),
                port=getattr(settings, "redis_port", 6379),
                decode_responses=True,
            )

    def has_changed(self, url: str, content: Union[str, bytes]) -> ChangeCheckResult:
        """Compute content hash and atomically update Redis if changed.

        Returns a `ChangeCheckResult` with old and new hashes and the timestamp.
        """
        canonical = _canonicalize_url(url)
        new_hash = self._compute_hash(content)
        hash_key = f"page_hash:{canonical}"
        crawled_key = f"page_crawled_at:{canonical}"

        try:
            old_hash = self.redis.get(hash_key)

            if new_hash != old_hash:
                # Update cache (TTL 30 days)
                pipeline = self.redis.pipeline()
                pipeline.set(hash_key, new_hash, ex=86400 * 30)
                pipeline.set(crawled_key, datetime.utcnow().isoformat(), ex=86400 * 30)
                pipeline.execute()
                logger.info("Change detected for %s", canonical)
                return ChangeCheckResult(True, old_hash, new_hash, datetime.utcnow())

            return ChangeCheckResult(False, old_hash, new_hash, datetime.utcnow())

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Redis error during change detection for %s: %s", canonical, exc)
            # On Redis errors, return conservative result (treat as unchanged)
            return ChangeCheckResult(False, None, new_hash, datetime.utcnow())

    def get_last_crawled(self, url: str) -> Optional[datetime]:
        """Get timestamp of last successful crawl for a URL.

        Returns None if unknown or on error.
        """
        try:
            timestamp_str = self.redis.get(f"page_crawled_at:{_canonicalize_url(url)}")
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str)
        except Exception:
            logger.exception("Failed to read last crawled timestamp for %s", url)
        return None

    def needs_refresh(self, url: str, hours_threshold: int = 24) -> bool:
        """Check if URL needs refreshing based on last crawl age."""
        last_crawled = self.get_last_crawled(url)
        if not last_crawled:
            return True

        age = datetime.utcnow() - last_crawled
        return age > timedelta(hours=hours_threshold)

    def _compute_hash(self, content: Union[str, bytes]) -> str:
        """Compute SHA256 hash of content (accepts str or bytes)."""
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        return hashlib.sha256(content_bytes).hexdigest()


class FreshnessMonitor:
    """Monitor and update scheme freshness status."""

    PRIORITY_SCHEMES = [
        "PM-KISAN",
        "AYUSHMAN-BHARAT",
        "MGNREGA",
    ]
    STANDARD_REFRESH_HOURS = 168  # 7 days
    PRIORITY_REFRESH_HOURS = 24  # 1 day

    def __init__(
        self, db_session: AsyncSession, redis_client: Optional[redis.Redis] = None
    ):
        self.db = db_session
        self.change_detector = ChangeDetector(redis_client)
        # Use the parsed redis host/port from settings (backwards compatible)
        self.redis = redis_client or redis.Redis(
            host=getattr(settings, "redis_host", getattr(settings, "REDIS_HOST", "localhost")),
            port=getattr(settings, "redis_port", getattr(settings, "REDIS_PORT", 6379)),
            decode_responses=True,
        )

    async def get_schemes_to_refresh(self) -> list[dict[str, str]]:
        """Return active schemes that should be refreshed now."""
        result = await self.db.execute(select(Scheme).where(Scheme.status == "active"))
        schemes = result.scalars().all()

        schemes_to_refresh: list[dict[str, str]] = []

        for scheme in schemes:
            is_priority = any(p in scheme.scheme_id for p in self.PRIORITY_SCHEMES)
            refresh_hours = self.PRIORITY_REFRESH_HOURS if is_priority else self.STANDARD_REFRESH_HOURS

            if self.change_detector.needs_refresh(scheme.official_url, hours_threshold=refresh_hours):
                schemes_to_refresh.append({
                    "scheme_id": scheme.scheme_id,
                    "url": scheme.official_url,
                    "priority": "high" if is_priority else "standard",
                })

        logger.info("Found %d schemes to refresh", len(schemes_to_refresh))
        return schemes_to_refresh

    async def mark_as_updated(self, scheme_id: str, content_hash: str, source_url: str):
        """Mark a scheme record as updated in the DB and commit."""
        result = await self.db.execute(select(Scheme).where(Scheme.scheme_id == scheme_id))
        scheme = result.scalar_one_or_none()

        if scheme:
            scheme.last_updated = datetime.utcnow()
            scheme.content_hash = content_hash
            await self.db.commit()
            logger.info("Updated freshness for %s", scheme_id)

    def get_freshness_stats(self, url: str) -> dict[str, object]:
        """Return freshness stats for a URL: last crawled, age hours and needs_refresh."""
        last_crawled = self.change_detector.get_last_crawled(url)
        if not last_crawled:
            return {"url": url, "last_crawled": None, "age_hours": None, "needs_refresh": True}

        age_hours = (datetime.utcnow() - last_crawled).total_seconds() / 3600
        needs_refresh = self.change_detector.needs_refresh(url)

        return {
            "url": url,
            "last_crawled": last_crawled.isoformat(),
            "age_hours": round(age_hours, 2),
            "needs_refresh": needs_refresh,
        }


class VersionTracker:
    """Track and manage scheme version history (placeholder).

    In a production system this would insert version rows into a
    `scheme_versions` table and support rollbacks / diffs.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def store_version(self, scheme_id: str, content: str, source_url: str, content_hash: str, metadata: dict | None = None):
        version_data = {
            "scheme_id": scheme_id,
            "content_hash": content_hash,
            "source_url": source_url,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        logger.info("Stored version for %s: %s", scheme_id, content_hash[:8])
        return version_data

    async def get_version_history(self, scheme_id: str, limit: int = 10) -> list[dict]:
        logger.info("Retrieving history for %s", scheme_id)
        return []
