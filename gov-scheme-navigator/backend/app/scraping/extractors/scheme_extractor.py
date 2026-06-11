"""
LLM-based structured extraction for government schemes.
Uses Gemini API for schema-compliant extraction from HTML/text.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import ValidationError

from app.scraping.extractors.schemas import ExtractionResult, SchemeSchema
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class SchemeExtractor:
    """Extract structured scheme information from raw content using LLM."""

    EXTRACTION_PROMPT_TEMPLATE = """
You are an expert government scheme analyst. Extract structured information from the given content
and return valid JSON matching the provided schema.

SCHEMA:
{{
  "scheme_id": "string (e.g., PM-KISAN-001)",
  "name": "string",
  "name_hindi": "string or null",
  "department": "string or null",
  "ministry": "string or null",
  "state": "string or null (e.g., 'Central', 'UP')",
  "category": ["list of categories, e.g., agriculture, education"],
  "target_beneficiaries": ["list of beneficiary types"],
  "eligibility": {{
    "age_min": "integer or null",
    "age_max": "integer or null",
    "income_max": "float or null",
    "land_ownership_required": "boolean or null",
    "land_hectares_max": "float or null",
    "occupation": ["list of occupations"],
    "states": ["list of states or 'all'"],
    "exclusions": ["list of exclusions"]
  }},
  "benefits": {{
    "type": "string (e.g., cash_transfer, scholarship)",
    "amount": "float or null",
    "frequency": "string (e.g., annual, monthly)",
    "installments": "integer or null",
    "description": "string"
  }},
  "documents_required": ["list of documents"],
  "application_process": ["list of steps or methods"],
  "status": "string (active, inactive, pending)"
}}

CONTENT TO EXTRACT:
{content}

INSTRUCTIONS:
1. Extract only what is explicitly stated in the content
2. Use null for unknown/missing fields
3. Be precise with numbers and dates
4. For eligibility criteria, extract exact values where available
5. Return ONLY valid JSON, no additional text
6. Set confidence to 0.8-1.0 based on clarity of information

Return JSON with 'record' and 'confidence' fields.
"""

    def __init__(self):
        """Initialize SchemeExtractor with Gemini API if available."""
        self.use_llm = genai is not None and settings.GEMINI_API_KEY
        if self.use_llm:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-pro")
        else:
            logger.warning("Gemini API not configured. Using fallback extraction.")
            self.model = None

    def extract(
        self, raw_content: str, source_url: str | None = None
    ) -> ExtractionResult:
        """
        Extract structured scheme information from raw content.

        Args:
            raw_content: Raw HTML/text content from web page
            source_url: Source URL for context

        Returns:
            ExtractionResult with Pydantic-validated schema
        """
        try:
            if self.use_llm and self.model:
                result = self._extract_with_llm(raw_content, source_url)
            else:
                result = self._extract_with_fallback(raw_content, source_url)

            return result

        except ValidationError as e:
            logger.error(f"Validation error during extraction: {e}")
            # Return empty result with low confidence
            return ExtractionResult(
                record=self._create_empty_scheme(),
                confidence=0.0,
            )
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return ExtractionResult(
                record=self._create_empty_scheme(),
                confidence=0.0,
            )

    def _extract_with_llm(
        self, raw_content: str, source_url: str | None
    ) -> ExtractionResult:
        """Extract using Gemini API."""
        # Truncate content if too long (API limits)
        content_truncated = raw_content[:4000]

        prompt = self.EXTRACTION_PROMPT_TEMPLATE.format(content=content_truncated)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Low temperature for consistency
                    "top_p": 0.9,
                    "top_k": 40,
                },
            )

            response_text = response.text

            # Extract JSON from response
            json_str = self._extract_json_from_text(response_text)
            data = json.loads(json_str)

            # Validate with Pydantic
            record = SchemeSchema(**data.get("record", {}))
            confidence = float(data.get("confidence", 0.5))

            logger.info(f"LLM extraction successful: {record.scheme_id}")
            return ExtractionResult(record=record, confidence=confidence)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise

    def _extract_with_fallback(
        self, raw_content: str, source_url: str | None
    ) -> ExtractionResult:
        """
        Fallback extraction using regex patterns.
        Simpler but lower quality than LLM.
        """
        import re

        # Extract basic fields using patterns
        scheme_name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", raw_content)
        scheme_name = scheme_name_match.group(1).strip() if scheme_name_match else "Unknown"

        # Extract eligibility patterns
        age_match = re.search(r"age.*?(\d+)\s*-\s*(\d+)", raw_content, re.IGNORECASE)
        income_match = re.search(r"income.*?₹?\s*([\d,]+)", raw_content, re.IGNORECASE)

        scheme_id = f"{scheme_name.replace(' ', '-').upper()}-001"

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

        logger.warning(f"Using fallback extraction for {scheme_id} (low confidence)")
        return ExtractionResult(record=record, confidence=0.4)

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON object from text response."""
        import re

        # Find JSON block in response
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            return json_match.group(0)

        # Try to find nested JSON
        brace_start = text.find("{")
        if brace_start != -1:
            brace_count = 0
            for i, char in enumerate(text[brace_start:]):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return text[brace_start : brace_start + i + 1]

        raise ValueError("No valid JSON found in response")

    def _create_empty_scheme(self) -> SchemeSchema:
        """Create an empty scheme for error cases."""
        return SchemeSchema(
            scheme_id="UNKNOWN-001",
            name="Unknown Scheme",
            status="inactive",
        )

