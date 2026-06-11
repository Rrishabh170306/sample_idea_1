from __future__ import annotations

from app.scraping.extractors.schemas import ExtractionResult


class SchemeExtractor:
    def extract(self, raw_content: str, source_url: str | None = None) -> ExtractionResult:
        raise NotImplementedError("Structured extraction will be implemented here.")
