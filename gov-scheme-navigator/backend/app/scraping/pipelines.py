"""
Scrapy pipelines for scheme data normalization and storage.
Integrates with change detection and embedding generation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scheme
from app.scraping.change_detector import VersionTracker, ChangeDetector
from app.rag.embedder import EmbeddingService

logger = logging.getLogger(__name__)


class NormalizeItemPipeline:
    """
    Normalize scheme data to match database schema.
    Handles missing fields, type conversions, validation.
    """

    REQUIRED_FIELDS = [
        "scheme_id",
        "name",
        "official_url",
    ]

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db = db_session
        self.skipped = 0
        self.normalized = 0

    def process_item(self, item: dict[str, object]) -> dict[str, object]:
        """
        Normalize scheme item.

        Args:
            item: Raw extracted scheme data

        Returns:
            Normalized item or raises DropItem
        """
        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if not item.get(field):
                logger.warning(f"Missing required field: {field} in {item.get('name')}")
                self.skipped += 1
                raise ValueError(f"Missing required field: {field}")

        # Type conversions
        item["benefits"] = self._normalize_benefits(item.get("benefits", {}))
        item["eligibility"] = self._normalize_eligibility(item.get("eligibility", {}))
        item["category"] = self._normalize_list(item.get("category", []))
        item["documents_required"] = self._normalize_list(item.get("documents_required", []))
        item["application_process"] = self._normalize_list(
            item.get("application_process", [])
        )

        # Ensure schema compliance
        item["status"] = str(item.get("status", "active")).lower()
        item["crawled_at"] = str(item.get("crawled_at", datetime.utcnow().isoformat()))

        self.normalized += 1
        logger.info(f"Normalized scheme: {item.get('scheme_id')}")
        return item

    def _normalize_benefits(self, benefits: dict | None) -> dict:
        """Normalize benefit fields."""
        if not benefits:
            return {}

        normalized = {
            "type": str(benefits.get("type", "")).lower() or None,
            "amount": self._to_float(benefits.get("amount")),
            "frequency": str(benefits.get("frequency", "")).lower() or None,
            "installments": self._to_int(benefits.get("installments")),
            "description": str(benefits.get("description", "")) or None,
        }
        return normalized

    def _normalize_eligibility(self, eligibility: dict | None) -> dict:
        """Normalize eligibility fields."""
        if not eligibility:
            return {}

        normalized = {
            "age_min": self._to_int(eligibility.get("age_min")),
            "age_max": self._to_int(eligibility.get("age_max")),
            "income_max": self._to_float(eligibility.get("income_max")),
            "land_ownership_required": bool(eligibility.get("land_ownership_required")),
            "land_hectares_max": self._to_float(eligibility.get("land_hectares_max")),
            "occupation": self._normalize_list(eligibility.get("occupation", [])),
            "states": self._normalize_list(eligibility.get("states", [])),
            "exclusions": self._normalize_list(eligibility.get("exclusions", [])),
        }
        return normalized

    def _normalize_list(self, value: list | str | None) -> list[str]:
        """Convert various types to list of strings."""
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        elif isinstance(value, str):
            return [value.strip()] if value.strip() else []
        return []

    def _to_float(self, value) -> Optional[float]:
        """Safe conversion to float."""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _to_int(self, value) -> Optional[int]:
        """Safe conversion to int."""
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def close_spider(self, spider):
        logger.info(f"Pipeline closed. Normalized: {self.normalized}, Skipped: {self.skipped}")


class StoragePipeline:
    """
    Persist normalized scheme data to database.
    Updates existing schemes or creates new ones.
    """

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.db = db_session
        self.embedding_service = embedding_service
        self.version_tracker = VersionTracker(db_session) if db_session else None
        self.stored = 0
        self.updated = 0
        self.change_detector = ChangeDetector() if db_session else None

    async def process_item(self, item: dict[str, object]) -> dict[str, object]:
        """
        Store scheme to database.
        Creates new record or updates existing one.

        Args:
            item: Normalized scheme item

        Returns:
            Stored item
        """
        if not self.db:
            logger.error("Database session not available")
            return item

        try:
            scheme_id = item.get("scheme_id")

            # Check if scheme exists
            result = await self.db.execute(
                select(Scheme).where(Scheme.scheme_id == scheme_id)
            )
            existing_scheme = result.scalar_one_or_none()

            if existing_scheme:
                # Update existing
                await self._update_scheme(existing_scheme, item)
                self.updated += 1
                logger.info(f"Updated scheme: {scheme_id}")
            else:
                # Create new
                await self._create_scheme(item)
                self.stored += 1
                logger.info(f"Created new scheme: {scheme_id}")

            # Generate embeddings if service available
            if self.embedding_service:
                await self._generate_embeddings(item)

            # Check for content changes (debounced by ChangeDetector)
            try:
                content_for_hash = str(item.get("content") or item.get("name") or "").encode("utf-8")
                if self.change_detector and item.get("official_url"):
                    change_res = self.change_detector.has_changed(str(item.get("official_url")), content_for_hash)
                    # Attach change metadata
                    item["_change_detected"] = change_res.changed
                    item["_old_hash"] = change_res.old_hash
                    item["_new_hash"] = change_res.new_hash
            except Exception:
                logger.debug("Could not compute change detection for item %s", item.get("scheme_id"), exc_info=True)

            # Track version
            if self.version_tracker:
                await self.version_tracker.store_version(
                    scheme_id=str(scheme_id),
                    content=str(item.get("name", "")),
                    source_url=str(item.get("source_url", "")),
                    content_hash=str(item.get("content_hash", "")),
                    metadata={
                        "confidence": float(item.get("confidence_score", 0.0)),
                        "extraction_method": "llm",
                    },
                )

            await self.db.commit()
            return item

        except Exception as e:
            logger.error(f"Error storing scheme {item.get('scheme_id')}: {e}")
            await self.db.rollback()
            raise

    async def _create_scheme(self, item: dict[str, object]):
        """Create new scheme record in database."""
        scheme = Scheme(
            scheme_id=item.get("scheme_id"),
            name=item.get("name"),
            name_hindi=item.get("name_hindi"),
            department=item.get("department"),
            ministry=item.get("ministry"),
            state=item.get("state"),
            category=item.get("category", []),
            target_beneficiaries=item.get("target_beneficiaries", []),
            eligibility=item.get("eligibility", {}),
            benefits=item.get("benefits", {}),
            documents_required=item.get("documents_required", []),
            application_process=item.get("application_process", []),
            official_url=item.get("official_url"),
            status=item.get("status", "active"),
            source_url=item.get("source_url"),
            content_hash=item.get("content_hash"),
            confidence_score=item.get("confidence_score", 0.0),
            crawled_at=item.get("crawled_at"),
        )
        self.db.add(scheme)

    async def _update_scheme(self, scheme: Scheme, item: dict[str, object]):
        """Update existing scheme record."""
        scheme.name = item.get("name", scheme.name)
        scheme.name_hindi = item.get("name_hindi", scheme.name_hindi)
        scheme.department = item.get("department", scheme.department)
        scheme.ministry = item.get("ministry", scheme.ministry)
        scheme.state = item.get("state", scheme.state)
        scheme.category = item.get("category", scheme.category)
        scheme.target_beneficiaries = item.get(
            "target_beneficiaries", scheme.target_beneficiaries
        )
        scheme.eligibility = item.get("eligibility", scheme.eligibility)
        scheme.benefits = item.get("benefits", scheme.benefits)
        scheme.documents_required = item.get(
            "documents_required", scheme.documents_required
        )
        scheme.application_process = item.get(
            "application_process", scheme.application_process
        )
        scheme.official_url = item.get("official_url", scheme.official_url)
        scheme.status = item.get("status", scheme.status)
        scheme.source_url = item.get("source_url", scheme.source_url)
        scheme.content_hash = item.get("content_hash", scheme.content_hash)
        scheme.confidence_score = item.get("confidence_score", scheme.confidence_score)
        scheme.last_updated = datetime.utcnow()

    async def _generate_embeddings(self, item: dict[str, object]):
        """Generate embeddings for scheme description and benefits."""
        scheme_id = item.get("scheme_id")
        text_to_embed = f"{item.get('name')} {item.get('benefits', {}).get('description', '')}"
        try:
            # The EmbeddingService provides a synchronous `embed_texts` method that
            # returns a list of embeddings for the provided texts.
            embeddings = self.embedding_service.embed_texts([text_to_embed])
            embedding = embeddings[0] if embeddings else None
            if embedding is not None:
                # Attach embedding to item for downstream storage or vector upsert
                item["_embedding"] = embedding
                logger.info("Generated embedding for %s", scheme_id)
            else:
                logger.debug("No embedding generated for %s", scheme_id)
        except Exception as e:
            logger.error("Failed to generate embedding for %s: %s", scheme_id, e)

    def close_spider(self, spider):
        logger.info(f"Storage complete. Stored: {self.stored}, Updated: {self.updated}")

