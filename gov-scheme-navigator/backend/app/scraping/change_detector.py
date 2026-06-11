"""
Change detection and freshness monitoring for web scraping.
Uses Redis for fast hash-based change tracking and manages version history.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scheme
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Hash-based change detection with Redis caching."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )

    def has_changed(self, url: str, content: str) -> bool:
        """
        Check if page content has changed using SHA256 hash.

        Args:
            url: URL of the page
            content: Raw HTML/text content

        Returns:
            True if content differs from cached hash, False otherwise
        """
        new_hash = self._compute_hash(content)
        old_hash = self.redis.get(f"page_hash:{url}")

        if new_hash != old_hash:
            # Update cache
            self.redis.set(f"page_hash:{url}", new_hash, ex=86400 * 30)  # 30 days TTL
            self.redis.set(
                f"page_crawled_at:{url}", datetime.utcnow().isoformat(), ex=86400 * 30
            )
            logger.info(f"Change detected for {url}")
            return True

        return False

    def get_last_crawled(self, url: str) -> Optional[datetime]:
        """Get timestamp of last successful crawl for a URL."""
        timestamp_str = self.redis.get(f"page_crawled_at:{url}")
        if timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        return None

    def needs_refresh(self, url: str, hours_threshold: int = 24) -> bool:
        """
        Check if URL needs refreshing based on age.

        Args:
            url: URL to check
            hours_threshold: Minimum hours since last crawl

        Returns:
            True if page should be re-crawled
        """
        last_crawled = self.get_last_crawled(url)
        if not last_crawled:
            return True

        age = datetime.utcnow() - last_crawled
        return age > timedelta(hours=hours_threshold)

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class FreshnessMonitor:
    """Monitor and update scheme freshness status."""

    PRIORITY_SCHEMES = [
        "PM-KISAN",
        "AYUSHMAN-BHARAT",
        "MGNREGA",
    ]  # High-priority schemes (daily refresh)
    STANDARD_REFRESH_HOURS = 168  # 7 days for most schemes
    PRIORITY_REFRESH_HOURS = 24  # 1 day for high-priority schemes

    def __init__(
        self, db_session: AsyncSession, redis_client: Optional[redis.Redis] = None
    ):
        self.db = db_session
        self.change_detector = ChangeDetector(redis_client)
        self.redis = redis_client or redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )

    async def get_schemes_to_refresh(self) -> list[dict[str, str]]:
        """
        Get schemes that need refreshing based on priority and age.

        Returns:
            List of scheme dicts with 'scheme_id', 'url', and 'priority'
        """
        result = await self.db.execute(
            select(Scheme).where(Scheme.status == "active")
        )
        schemes = result.scalars().all()

        schemes_to_refresh = []

        for scheme in schemes:
            is_priority = any(
                priority_scheme in scheme.scheme_id
                for priority_scheme in self.PRIORITY_SCHEMES
            )
            refresh_hours = (
                self.PRIORITY_REFRESH_HOURS
                if is_priority
                else self.STANDARD_REFRESH_HOURS
            )

            if self.change_detector.needs_refresh(
                scheme.official_url, hours_threshold=refresh_hours
            ):
                schemes_to_refresh.append({
                    "scheme_id": scheme.scheme_id,
                    "url": scheme.official_url,
                    "priority": "high" if is_priority else "standard",
                })

        logger.info(f"Found {len(schemes_to_refresh)} schemes to refresh")
        return schemes_to_refresh

    async def mark_as_updated(
        self, scheme_id: str, content_hash: str, source_url: str
    ):
        """
        Mark a scheme as updated and store version.

        Args:
            scheme_id: Scheme ID
            content_hash: Hash of current content
            source_url: URL source
        """
        # Update scheme record
        result = await self.db.execute(
            select(Scheme).where(Scheme.scheme_id == scheme_id)
        )
        scheme = result.scalar_one_or_none()

        if scheme:
            scheme.last_updated = datetime.utcnow()
            scheme.content_hash = content_hash
            await self.db.commit()
            logger.info(f"Updated freshness for {scheme_id}")

    def get_freshness_stats(self, url: str) -> dict[str, any]:
        """
        Get detailed freshness statistics for a URL.

        Returns:
            Dict with 'last_crawled', 'age_hours', 'needs_refresh' keys
        """
        last_crawled = self.change_detector.get_last_crawled(url)
        if not last_crawled:
            age_hours = None
            needs_refresh = True
        else:
            age_hours = (datetime.utcnow() - last_crawled).total_seconds() / 3600
            needs_refresh = self.change_detector.needs_refresh(url)

        return {
            "url": url,
            "last_crawled": last_crawled.isoformat() if last_crawled else None,
            "age_hours": round(age_hours, 2) if age_hours else None,
            "needs_refresh": needs_refresh,
        }


class VersionTracker:
    """Track and manage scheme version history."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def store_version(
        self,
        scheme_id: str,
        content: str,
        source_url: str,
        content_hash: str,
        metadata: dict = None,
    ):
        """
        Store a version snapshot of a scheme.

        Args:
            scheme_id: Scheme ID
            content: Full content
            source_url: Source URL
            content_hash: Content hash
            metadata: Additional metadata (changes, confidence, etc.)
        """
        # Placeholder for version storage in scheme_versions table
        # This would typically store in a PostgreSQL table
        version_data = {
            "scheme_id": scheme_id,
            "content_hash": content_hash,
            "source_url": source_url,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        logger.info(f"Stored version for {scheme_id}: {content_hash[:8]}...")
        return version_data

    async def get_version_history(self, scheme_id: str, limit: int = 10) -> list[dict]:
        """
        Retrieve version history for a scheme.

        Args:
            scheme_id: Scheme ID
            limit: Maximum versions to retrieve

        Returns:
            List of version records
        """
        # Placeholder implementation
        logger.info(f"Retrieving history for {scheme_id}")
        return []
