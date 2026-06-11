"""
Point 2: Knowledge Extraction System
Handles LLM-based extraction, validation, confidence scoring, and manual review queue.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import Column, String, Float, JSON, DateTime, Boolean, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()


class ExtractionStatus(str, Enum):
    """Status of extraction process."""
    PENDING = "pending"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    REVIEW_NEEDED = "review_needed"
    APPROVED = "approved"
    REJECTED = "rejected"


# ============================================================================
# 1. ENHANCED SCHEME SCHEMA (Pydantic Models)
# ============================================================================


class DocumentSchema(BaseModel):
    """Document requirement details."""
    type: str
    name: str
    optional: bool = False
    upload_link: Optional[str] = None


class AgeSchema(BaseModel):
    """Age eligibility criteria."""
    min: Optional[int] = None
    max: Optional[int] = None


class LandOwnershipSchema(BaseModel):
    """Land ownership eligibility criteria."""
    required: bool = False
    max_hectares: Optional[float] = None


class EligibilitySchema(BaseModel):
    """Enhanced eligibility schema."""
    age: AgeSchema = Field(default_factory=AgeSchema)
    income: Optional[dict[str, float]] = None  # {"max": 500000, "type": "annual"}
    land_ownership: LandOwnershipSchema = Field(default_factory=LandOwnershipSchema)
    occupation: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    caste_category: Optional[list[str]] = None  # ["SC", "ST", "OBC"]
    gender_specific: Optional[str] = None  # "male", "female", "any"
    marital_status: Optional[list[str]] = None  # ["married", "single"]


class BenefitsSchema(BaseModel):
    """Enhanced benefits schema."""
    type: str  # "cash_transfer", "scholarship", "subsidy", etc.
    amount: Optional[float] = None
    frequency: str  # "annual", "monthly", "one-time"
    installments: Optional[int] = None
    description: str
    currency: str = "INR"


class SchemeMetadataSchema(BaseModel):
    """Metadata for scheme record."""
    source_urls: list[str] = Field(default_factory=list)
    content_hash: Optional[str] = None
    last_updated: datetime
    extracted_at: datetime
    extraction_method: str = "llm"  # "llm", "regex", "manual"


class EnhancedSchemeSchema(BaseModel):
    """Complete scheme schema with all details."""
    scheme_id: str
    name: str
    name_hindi: Optional[str] = None
    department: Optional[str] = None
    ministry: Optional[str] = None
    state: str  # "Central", "UP", etc.
    category: list[str] = Field(default_factory=list)
    target_beneficiaries: list[str] = Field(default_factory=list)
    eligibility: EligibilitySchema = Field(default_factory=EligibilitySchema)
    benefits: BenefitsSchema = Field(default_factory=BenefitsSchema)
    documents_required: list[DocumentSchema] = Field(default_factory=list)
    application_process: list[str] = Field(default_factory=list)
    official_url: Optional[str] = None
    deadline: Optional[datetime] = None
    status: str = "active"  # "active", "inactive", "pending"
    metadata: SchemeMetadataSchema
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ExtractionResultSchema(BaseModel):
    """Result of extraction process."""
    extraction_id: str = Field(default_factory=lambda: str(uuid4()))
    raw_content: str
    extracted_scheme: EnhancedSchemeSchema
    confidence_score: float  # 0.0 to 1.0
    extraction_status: ExtractionStatus = ExtractionStatus.EXTRACTED
    errors: list[str] = Field(default_factory=list)
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# 2. EXTRACTION PIPELINE
# ============================================================================


class ExtractionPipeline:
    """
    Main extraction pipeline: Raw content → LLM extraction → Validation
    """

    def __init__(self):
        self.extractor = LLMSchemeExtractor()
        self.validator = SchemaValidator()

    async def process(self, raw_content: str, source_url: str) -> ExtractionResultSchema:
        """
        Process raw content through full extraction pipeline.

        Args:
            raw_content: Raw HTML/text content
            source_url: Source URL for context

        Returns:
            ExtractionResultSchema with results
        """
        extraction_id = str(uuid4())
        errors = []

        try:
            # Step 1: LLM extraction
            logger.info(f"[{extraction_id}] Starting LLM extraction...")
            extracted_dict = await self.extractor.extract(raw_content, source_url)

            # Step 2: Schema validation
            logger.info(f"[{extraction_id}] Validating schema...")
            metadata = SchemeMetadataSchema(
                source_urls=[source_url],
                last_updated=datetime.utcnow(),
                extracted_at=datetime.utcnow(),
                extraction_method="llm"
            )
            
            extracted_dict["metadata"] = metadata.model_dump()
            scheme = EnhancedSchemeSchema(**extracted_dict)

            # Step 3: Confidence scoring
            confidence = self._calculate_confidence(scheme)
            status = (
                ExtractionStatus.REVIEW_NEEDED
                if confidence < 0.8
                else ExtractionStatus.VALIDATED
            )

            logger.info(
                f"[{extraction_id}] Extraction successful. "
                f"Confidence: {confidence:.2f}, Status: {status}"
            )

            return ExtractionResultSchema(
                extraction_id=extraction_id,
                raw_content=raw_content[:500],  # Store truncated content
                extracted_scheme=scheme,
                confidence_score=confidence,
                extraction_status=status,
                errors=errors,
            )

        except ValidationError as e:
            logger.error(f"[{extraction_id}] Validation error: {e}")
            errors.append(f"Validation failed: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"[{extraction_id}] Extraction error: {e}")
            errors.append(f"Extraction failed: {str(e)}")
            raise

    def _calculate_confidence(self, scheme: EnhancedSchemeSchema) -> float:
        """
        Calculate extraction confidence based on field completeness.
        
        Args:
            scheme: Extracted scheme
            
        Returns:
            Confidence score 0.0-1.0
        """
        total_fields = 0
        filled_fields = 0

        # Check required fields
        required = [
            (scheme.scheme_id, "scheme_id"),
            (scheme.name, "name"),
            (scheme.official_url, "official_url"),
        ]

        for value, name in required:
            total_fields += 1
            if value:
                filled_fields += 1
            else:
                logger.warning(f"Required field missing: {name}")

        # Check optional but important fields
        important = [
            (scheme.eligibility.occupation, "occupation"),
            (scheme.benefits.description, "benefits_description"),
            (scheme.documents_required, "documents_required"),
        ]

        for value, name in important:
            total_fields += 1
            if value:
                filled_fields += 1

        confidence = filled_fields / total_fields if total_fields > 0 else 0.0
        return min(confidence + 0.1, 1.0)  # Boost slightly for successful extraction


class LLMSchemeExtractor:
    """Extract structured scheme data using LLM (Gemini)."""

    EXTRACTION_PROMPT = """
    Extract structured government scheme information from the given content.
    Return ONLY valid JSON matching this structure:
    {{
        "scheme_id": "string",
        "name": "string",
        "name_hindi": "string or null",
        "department": "string or null",
        "ministry": "string or null",
        "state": "string",
        "category": ["array of categories"],
        "target_beneficiaries": ["array"],
        "eligibility": {{
            "age": {{"min": int or null, "max": int or null}},
            "income": {{"max": number or null}},
            "land_ownership": {{"required": bool, "max_hectares": number or null}},
            "occupation": ["array"],
            "states": ["array"],
            "exclusions": ["array"],
            "caste_category": ["array or null"],
            "gender_specific": "string or null",
            "marital_status": ["array or null"]
        }},
        "benefits": {{
            "type": "string",
            "amount": number or null,
            "frequency": "string",
            "installments": int or null,
            "description": "string",
            "currency": "INR"
        }},
        "documents_required": [{{"type": "string", "name": "string", "optional": bool}}],
        "application_process": ["array of steps"],
        "official_url": "string or null",
        "deadline": "ISO datetime or null",
        "status": "active|inactive|pending"
    }}
    
    Content to extract from:
    {content}
    """

    async def extract(self, content: str, source_url: str) -> dict:
        """
        Extract scheme using LLM.
        Falls back to regex extraction if LLM unavailable.
        """
        try:
            # Try LLM extraction
            result = await self._llm_extract(content)
            return result
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}. Using fallback...")
            return self._regex_extract(content, source_url)

    async def _llm_extract(self, content: str) -> dict:
        """LLM-based extraction (requires Gemini API)."""
        try:
            import google.generativeai as genai
            from app.core.config import settings

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-pro")

            prompt = self.EXTRACTION_PROMPT.format(content=content[:3000])
            response = model.generate_content(prompt)
            
            json_str = self._extract_json(response.text)
            return json.loads(json_str)
        except Exception as e:
            raise e

    def _regex_extract(self, content: str, source_url: str) -> dict:
        """Fallback regex-based extraction."""
        import re
        from urllib.parse import urlparse

        # Extract basic fields using patterns
        name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", content)
        scheme_name = name_match.group(1).strip() if name_match else "Unknown"

        domain = urlparse(source_url).netloc
        scheme_id = f"{scheme_name.replace(' ', '-').upper()}-001"

        return {
            "scheme_id": scheme_id,
            "name": scheme_name,
            "official_url": source_url,
            "state": "Central",
            "category": ["general"],
            "target_beneficiaries": ["citizens"],
            "eligibility": {
                "age": {"min": None, "max": None},
                "income": {"max": None},
                "land_ownership": {"required": False, "max_hectares": None},
                "occupation": [],
                "states": [],
                "exclusions": [],
                "caste_category": None,
                "gender_specific": None,
                "marital_status": None
            },
            "benefits": {
                "type": "general",
                "amount": None,
                "frequency": "unknown",
                "installments": None,
                "description": "Government scheme",
                "currency": "INR"
            },
            "documents_required": [],
            "application_process": [],
            "status": "active",
        }

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text response."""
        import re
        
        brace_start = text.find("{")
        if brace_start == -1:
            raise ValueError("No JSON found in response")

        brace_count = 0
        for i, char in enumerate(text[brace_start:]):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    return text[brace_start : brace_start + i + 1]

        raise ValueError("Malformed JSON in response")


class SchemaValidator:
    """Validate extracted schemes against schema."""

    def validate(self, data: dict) -> tuple[bool, list[str]]:
        """
        Validate data against schema.
        
        Returns:
            (is_valid, list of error messages)
        """
        errors = []

        # Required fields
        required_fields = ["scheme_id", "name", "benefits"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate eligibility
        eligibility = data.get("eligibility", {})
        if eligibility and "occupation" in eligibility:
            if not isinstance(eligibility["occupation"], list):
                errors.append("Eligibility.occupation must be a list")

        return len(errors) == 0, errors


# ============================================================================
# 3. MANUAL REVIEW QUEUE SYSTEM
# ============================================================================


class ExtractionReviewRecord(Base):
    """Database model for extraction reviews."""
    __tablename__ = "extraction_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    extraction_id = Column(String(36), nullable=False, unique=True)
    scheme_id = Column(String(100), nullable=False)
    raw_content = Column(String, nullable=False)
    extracted_data = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=False)
    review_status = Column(String(50), default="pending")
    reviewer_id = Column(String(100), nullable=True)
    approval_status = Column(String(50), nullable=True)  # "approved", "rejected", "needs_revision"
    reviewer_feedback = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class ManualReviewQueue:
    """
    Manage manual review queue for low-confidence extractions.
    Routes extractions with confidence < 0.8 for human review.
    """

    LOW_CONFIDENCE_THRESHOLD = 0.8

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def add_to_review(self, result: ExtractionResultSchema) -> str:
        """
        Add extraction to review queue if confidence is low.
        
        Returns:
            Review ID or None if not added
        """
        if result.confidence_score >= self.LOW_CONFIDENCE_THRESHOLD:
            logger.info(
                f"Extraction {result.extraction_id} has sufficient confidence. "
                "Skipping review."
            )
            return None

        logger.warning(
            f"Low confidence ({result.confidence_score:.2f}) for "
            f"{result.extracted_scheme.scheme_id}. Adding to review queue."
        )

        review = ExtractionReviewRecord(
            extraction_id=result.extraction_id,
            scheme_id=result.extracted_scheme.scheme_id,
            raw_content=result.raw_content,
            extracted_data=result.extracted_scheme.model_dump(),
            confidence_score=result.confidence_score,
            review_status="pending",
        )

        self.db.add(review)
        await self.db.commit()

        logger.info(f"Added to review queue: {review.id}")
        return review.id

    async def fetch_pending_reviews(self, limit: int = 10) -> list[ExtractionReviewRecord]:
        """Fetch pending reviews for human reviewer."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(ExtractionReviewRecord).where(
                ExtractionReviewRecord.review_status == "pending"
            ).limit(limit)
        )
        return result.scalars().all()

    async def mark_reviewed(
        self,
        review_id: str,
        reviewer_id: str,
        approval_status: str,
        feedback: str = None,
    ):
        """Mark review as completed."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(ExtractionReviewRecord).where(
                ExtractionReviewRecord.id == review_id
            )
        )
        review = result.scalar_one_or_none()

        if review:
            review.reviewer_id = reviewer_id
            review.approval_status = approval_status
            review.reviewer_feedback = feedback
            review.review_status = "completed"
            review.reviewed_at = datetime.utcnow()
            await self.db.commit()
            logger.info(f"Marked review {review_id} as {approval_status}")

    async def get_queue_stats(self) -> dict:
        """Get review queue statistics."""
        from sqlalchemy import select, func

        result = await self.db.execute(
            select(func.count(ExtractionReviewRecord.id)).where(
                ExtractionReviewRecord.review_status == "pending"
            )
        )
        pending_count = result.scalar() or 0

        result = await self.db.execute(
            select(func.avg(ExtractionReviewRecord.confidence_score))
        )
        avg_confidence = result.scalar() or 0.0

        return {
            "pending_reviews": pending_count,
            "average_confidence": round(avg_confidence, 3),
        }


# ============================================================================
# 4. BATCH EXTRACTION PROCESSOR
# ============================================================================


class BatchExtractionProcessor:
    """Process multiple schemes in parallel with aggregated stats."""

    def __init__(self, db_session: AsyncSession, batch_size: int = 5):
        self.db = db_session
        self.batch_size = batch_size
        self.pipeline = ExtractionPipeline()
        self.review_queue = ManualReviewQueue(db_session)

    async def process_batch(
        self, items: list[dict[str, str]]
    ) -> dict[str, object]:
        """
        Process batch of items.
        
        Args:
            items: List of {"raw_content": str, "source_url": str}
            
        Returns:
            Batch statistics and results
        """
        import asyncio

        start_time = datetime.utcnow()
        results = []
        errors = []

        logger.info(f"Starting batch processing of {len(items)} items")

        # Process in parallel batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            tasks = [
                self._process_single(item, results, errors)
                for item in batch
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate statistics
        stats = self._calculate_stats(results, errors, start_time)
        logger.info(f"Batch processing complete: {stats}")

        return {
            "total_processed": len(items),
            "successful": len(results),
            "failed": len(errors),
            "statistics": stats,
            "results": results,
            "errors": errors,
        }

    async def _process_single(
        self, item: dict, results: list, errors: list
    ):
        """Process single item."""
        try:
            result = await self.pipeline.process(
                item["raw_content"], item["source_url"]
            )
            results.append(result.model_dump())

            # Check if needs review
            if result.extraction_status == ExtractionStatus.REVIEW_NEEDED:
                await self.review_queue.add_to_review(result)

        except Exception as e:
            logger.error(f"Error processing item: {e}")
            errors.append({"item": item.get("source_url"), "error": str(e)})

    def _calculate_stats(
        self, results: list, errors: list, start_time: datetime
    ) -> dict:
        """Calculate batch statistics."""
        import statistics

        if not results:
            return {
                "success_rate": 0.0,
                "average_confidence": 0.0,
                "processing_time_sec": (datetime.utcnow() - start_time).total_seconds(),
            }

        confidences = [r["confidence_score"] for r in results]

        return {
            "success_rate": len(results) / (len(results) + len(errors)) * 100,
            "average_confidence": round(statistics.mean(confidences), 3),
            "min_confidence": round(min(confidences), 3),
            "max_confidence": round(max(confidences), 3),
            "processing_time_sec": (datetime.utcnow() - start_time).total_seconds(),
        }
