"""
LLM-based structured extraction for government schemes.
Uses OpenRouter (OpenAI-compatible API) for schema-compliant extraction from HTML/text.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from app.scraping.extractors.schemas import ExtractionResult, SchemeSchema

logger = logging.getLogger(__name__)


class SchemeExtractor:
    """Extract structured scheme information from raw content using LLM."""

    EXTRACTION_PROMPT_TEMPLATE = """\
You are an expert Indian government scheme analyst. Extract structured information from the given content and return ONLY valid JSON matching the schema below.

SCHEMA:
{{
  "scheme_id": "string (slug-style, e.g. PM-KISAN-001)",
  "name": "string (full scheme name in English)",
  "name_hindi": "string or null",
  "department": "string or null",
  "ministry": "string or null",
  "state": "string (e.g. 'Central', 'Tamil Nadu', 'UP')",
  "category": ["list of categories, e.g. agriculture, education, health"],
  "target_beneficiaries": ["list of beneficiary types, e.g. farmers, women, students"],
  "eligibility": {{
    "age_min": "integer or null",
    "age_max": "integer or null",
    "income_max": "float or null (annual income in INR)",
    "land_ownership_required": "boolean or null",
    "land_hectares_max": "float or null",
    "occupation": ["list of occupations"],
    "states": ["list of eligible states or ['all']"],
    "exclusions": ["list of exclusions"]
  }},
  "benefits": {{
    "type": "string (e.g. cash_transfer, scholarship, subsidy, credit, insurance)",
    "amount": "float or null",
    "frequency": "string (e.g. annual, monthly, one_time)",
    "installments": "integer or null",
    "description": "string"
  }},
  "documents_required": ["list of required documents as strings"],
  "application_process": ["list of application steps"],
  "official_url": "string or null",
  "status": "active|inactive|pending"
}}

CONTENT TO EXTRACT FROM:
{content}

INSTRUCTIONS:
1. Extract only what is explicitly stated in the content
2. Use null for unknown/missing fields
3. Be precise with numbers and dates
4. Return ONLY valid JSON as a single object with fields "record" and "confidence" (0.0–1.0)
5. Set confidence to 0.9+ if the scheme name, eligibility and benefits are clearly stated; 0.5 otherwise
"""

    def __init__(self) -> None:
        """Initialize SchemeExtractor. LLM client is created per-call to respect env vars."""
        pass

    def extract(
        self, raw_content: str, source_url: str | None = None
    ) -> ExtractionResult:
        """
        Extract structured scheme information from raw content.

        Tries LLM extraction first (via OpenRouter), falls back to regex heuristics.

        Args:
            raw_content: Raw HTML/text content from web page
            source_url: Source URL for context

        Returns:
            ExtractionResult with Pydantic-validated schema
        """
        try:
            result = self._extract_with_llm(raw_content, source_url)
            return result
        except Exception as llm_exc:
            logger.warning("LLM extraction failed (%s), using regex fallback", llm_exc)
            try:
                return self._extract_with_fallback(raw_content, source_url)
            except ValidationError as e:
                logger.error("Fallback extraction validation error: %s", e)
                return ExtractionResult(record=self._create_empty_scheme(), confidence=0.0)
            except Exception as e:
                logger.error("Fallback extraction error: %s", e)
                return ExtractionResult(record=self._create_empty_scheme(), confidence=0.0)

    def _extract_with_llm(
        self, raw_content: str, source_url: str | None
    ) -> ExtractionResult:
        """Extract using the unified LLM client (OpenRouter)."""
        from app.llm.client import LLMClient

        # Truncate to stay within token limits (~4000 chars ≈ ~1000 tokens)
        content_truncated = raw_content[:5000]
        prompt = self.EXTRACTION_PROMPT_TEMPLATE.format(content=content_truncated)

        client = LLMClient()
        response_text = client.generate_sync(prompt, temperature=0.1, max_tokens=1500)

        # Parse JSON from response
        json_str = self._extract_json_from_text(response_text)
        data = json.loads(json_str)

        record_data = data.get("record") or data
        # Inject source_url if official_url not provided
        if not record_data.get("official_url") and source_url:
            record_data["official_url"] = source_url

        try:
            record = SchemeSchema(**record_data)
        except ValidationError as exc:
            logger.warning("Schema validation failed post-LLM, attempting repair: %s", exc)
            record = self._repair_and_validate(record_data, source_url)

        confidence = float(data.get("confidence", 0.7))
        logger.info("LLM extraction successful for %s (confidence=%.2f)", record.scheme_id, confidence)
        return ExtractionResult(record=record, confidence=confidence)

    def _repair_and_validate(
        self, data: dict, source_url: str | None
    ) -> SchemeSchema:
        """Attempt minimal repair of extracted data to pass validation."""
        data.setdefault("scheme_id", "UNKNOWN-001")
        data.setdefault("name", "Unknown Scheme")
        data.setdefault("status", "active")
        if source_url and not data.get("official_url"):
            data["official_url"] = source_url
        # Strip unknown nested fields that might cause issues
        for key in ("eligibility", "benefits"):
            if key in data and not isinstance(data[key], dict):
                del data[key]
        return SchemeSchema(**data)

    def _extract_with_fallback(
        self, raw_content: str, source_url: str | None
    ) -> ExtractionResult:
        """Regex-based fallback extraction when LLM is unavailable."""
        scheme_name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", raw_content)
        scheme_name = scheme_name_match.group(1).strip() if scheme_name_match else "Unknown"

        age_match = re.search(r"age.*?(\d+)\s*[-–]\s*(\d+)", raw_content, re.IGNORECASE)
        income_match = re.search(r"income.*?₹?\s*([\d,]+)", raw_content, re.IGNORECASE)

        # Derive a scheme_id from the name
        safe_name = re.sub(r"[^A-Z0-9]+", "-", scheme_name.upper())[:30]
        scheme_id = f"{safe_name}-001"

        record = SchemeSchema(
            scheme_id=scheme_id,
            name=scheme_name,
            official_url=source_url,
            status="active",
        )

        if age_match:
            record.eligibility.age_min = int(age_match.group(1))
            record.eligibility.age_max = int(age_match.group(2))

        if income_match:
            income_str = income_match.group(1).replace(",", "")
            try:
                record.eligibility.income_max = float(income_str)
            except ValueError:
                pass

        logger.warning("Used regex fallback extraction for %s (low confidence)", scheme_id)
        return ExtractionResult(record=record, confidence=0.4)

    def _extract_json_from_text(self, text: str) -> str:
        """Extract the outermost JSON object from a text response."""
        # Try to find first complete JSON object
        brace_start = text.find("{")
        if brace_start == -1:
            raise ValueError("No JSON object found in LLM response")

        brace_count = 0
        for i, char in enumerate(text[brace_start:]):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    return text[brace_start: brace_start + i + 1]

        raise ValueError("Malformed JSON in LLM response (unbalanced braces)")

    def _create_empty_scheme(self) -> SchemeSchema:
        """Create a minimal empty scheme for error-fallback cases."""
        return SchemeSchema(
            scheme_id="UNKNOWN-001",
            name="Unknown Scheme",
            status="inactive",
        )
