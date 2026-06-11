"""
PDF extraction and OCR pipeline with multilingual support.
Uses PyMuPDF for fast extraction and Tesseract for scanned documents.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

logger = logging.getLogger(__name__)


@dataclass
class ExtractedSection:
    """Represents a logical section of extracted text."""

    title: str
    content: str
    page_number: int
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""

    text: str
    sections: list[ExtractedSection]
    metadata: dict
    is_scanned: bool
    language: str = "en"
    extraction_method: str = "pdfminer"  # 'pdfminer', 'ocr', 'hybrid'


class PDFExtractor:
    """
    Extract text from PDFs using PyMuPDF.
    Handles both native PDFs and scanned documents.
    """

    SUPPORTED_LANGUAGES = ["en", "hi", "ta", "te", "kn", "ml"]  # Hindi and regional
    MIN_CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, use_ocr_fallback: bool = True):
        """
        Initialize PDFExtractor.

        Args:
            use_ocr_fallback: If True, use Tesseract for scanned PDFs
        """
        if not fitz:
            raise ImportError("fitz (PyMuPDF) is required. Install with: pip install PyMuPDF")

        self.use_ocr_fallback = use_ocr_fallback
        if use_ocr_fallback and not pytesseract:
            logger.warning(
                "pytesseract not installed. OCR fallback disabled. "
                "Install with: pip install pytesseract pillow"
            )
            self.use_ocr_fallback = False

    def extract(self, file_path: str) -> ExtractionResult:
        """
        Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            ExtractionResult with extracted text and metadata
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = fitz.open(file_path)
        sections = []
        all_text = []
        is_scanned = False
        metadata = {
            "filename": file_path.name,
            "total_pages": len(doc),
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "creation_date": doc.metadata.get("creation_date", ""),
        }

        for page_num, page in enumerate(doc, 1):
            # Try native text extraction first
            text = page.get_text("text")

            # If page is mostly blank, likely scanned
            if len(text.strip()) < 100:
                if self.use_ocr_fallback:
                    logger.info(f"Scanned page detected on page {page_num}. Using OCR.")
                    text = self._extract_via_ocr(page)
                    is_scanned = True
                else:
                    logger.warning(f"Scanned page detected but OCR disabled: page {page_num}")

            # Detect section headers (common patterns)
            extracted_section = self._extract_section(text, page_num)
            if extracted_section:
                sections.append(extracted_section)

            all_text.append(text)

        doc.close()

        # Clean and normalize text
        normalized_text = self._normalize_text("\n".join(all_text))

        return ExtractionResult(
            text=normalized_text,
            sections=sections,
            metadata=metadata,
            is_scanned=is_scanned,
            extraction_method="ocr" if is_scanned else "pdfminer",
        )

    def _extract_via_ocr(self, page: fitz.Page) -> str:
        """
        Extract text from page using Tesseract OCR.

        Args:
            page: PyMuPDF page object

        Returns:
            Extracted text
        """
        if not pytesseract or not Image:
            logger.error("OCR dependencies not available")
            return ""

        try:
            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution for better OCR
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Extract text with language support
            text = pytesseract.image_to_string(
                image,
                lang="hin+eng",  # Hindi + English
                config="--psm 3",  # Assume single column layout
            )

            return text
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    def _extract_section(self, text: str, page_num: int) -> Optional[ExtractedSection]:
        """
        Extract logical sections from page text.

        Args:
            text: Page text
            page_num: Page number

        Returns:
            ExtractedSection or None
        """
        lines = text.split("\n")
        if not lines:
            return None

        # First line often is section title
        title = lines[0].strip()
        if not title or len(title) < 5:
            return None

        content = "\n".join(lines[1:]).strip()
        return ExtractedSection(
            title=title,
            content=content,
            page_num=page_num,
            confidence=1.0,
        )

    def _normalize_text(self, text: str) -> str:
        """
        Normalize extracted text: remove excess whitespace, fix encoding.

        Args:
            text: Raw extracted text

        Returns:
            Normalized text
        """
        # Fix common encoding issues
        text = text.replace("\x00", "")
        text = re.sub(r"\s+", " ", text)  # Collapse whitespace
        text = re.sub(r" +\n", "\n", text)  # Remove trailing spaces
        return text.strip()


class ChunkingStrategy:
    """
    Chunk long documents respecting section boundaries.
    Implements parent-child chunking for better retrieval.
    """

    def __init__(
        self,
        child_chunk_size: int = 300,
        parent_chunk_size: int = 1500,
        overlap: int = 100,
    ):
        """
        Initialize chunking parameters.

        Args:
            child_chunk_size: Size of child chunks in tokens (approximate)
            parent_chunk_size: Size of parent chunks in tokens
            overlap: Token overlap between chunks
        """
        self.child_chunk_size = child_chunk_size
        self.parent_chunk_size = parent_chunk_size
        self.overlap = overlap
        self.avg_chars_per_token = 4  # Rough estimate

    def chunk_document(self, text: str, sections: list[ExtractedSection]) -> dict:
        """
        Create hierarchical chunks from document.

        Args:
            text: Full document text
            sections: Extracted sections

        Returns:
            Dict with 'parent_chunks' and 'child_chunks'
        """
        parent_chunks = []
        child_chunks = []

        # Create parent chunks with section awareness
        current_parent = ""
        for section in sections:
            section_text = f"{section.title}\n{section.content}"

            # Start new parent chunk if exceeds size
            if len(current_parent) + len(section_text) > self.parent_chunk_size * self.avg_chars_per_token:
                if current_parent:
                    parent_chunks.append({
                        "content": current_parent.strip(),
                        "section_headers": self._extract_headers(current_parent),
                    })
                current_parent = section_text
            else:
                current_parent += f"\n{section_text}"

        if current_parent:
            parent_chunks.append({
                "content": current_parent.strip(),
                "section_headers": self._extract_headers(current_parent),
            })

        # Create child chunks from parent chunks
        for parent in parent_chunks:
            child_list = self._split_into_chunks(
                parent["content"],
                self.child_chunk_size * self.avg_chars_per_token,
                self.overlap * self.avg_chars_per_token,
            )

            for child_text in child_list:
                child_chunks.append({
                    "content": child_text,
                    "parent_headers": parent["section_headers"],
                })

        return {
            "parent_chunks": parent_chunks,
            "child_chunks": child_chunks,
            "total_chunks": len(child_chunks),
        }

    def _split_into_chunks(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap
        return chunks

    def _extract_headers(self, text: str) -> list[str]:
        """Extract section headers from text."""
        lines = text.split("\n")
        headers = [line.strip() for line in lines[:3] if line.strip()]
        return headers


class PDFPipeline:
    """
    Complete PDF processing pipeline: extraction → chunking → storage.
    """

    def __init__(self, use_ocr: bool = True):
        self.extractor = PDFExtractor(use_ocr_fallback=use_ocr)
        self.chunker = ChunkingStrategy()

    async def process_pdf(self, file_path: str) -> dict:
        """
        Process PDF: extract, chunk, and prepare for storage.

        Args:
            file_path: Path to PDF file

        Returns:
            Dict with extraction results and chunks
        """
        try:
            # Extract text
            extraction_result = self.extractor.extract(file_path)
            logger.info(
                f"Extracted {len(extraction_result.text)} chars from {Path(file_path).name}"
            )

            # Chunk document
            chunking_result = self.chunker.chunk_document(
                extraction_result.text,
                extraction_result.sections,
            )

            return {
                "success": True,
                "extraction": extraction_result,
                "chunks": chunking_result,
                "stats": {
                    "total_text_length": len(extraction_result.text),
                    "total_sections": len(extraction_result.sections),
                    "is_scanned": extraction_result.is_scanned,
                    "extraction_method": extraction_result.extraction_method,
                    "parent_chunks": len(chunking_result["parent_chunks"]),
                    "child_chunks": len(chunking_result["child_chunks"]),
                },
            }

        except Exception as e:
            logger.error(f"PDF processing failed for {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
            }


async def extract_text(file_path: str) -> str:
    """
    Simple async wrapper for PDF text extraction.

    Args:
        file_path: Path to PDF file

    Returns:
        Extracted text content
    """
    loop = asyncio.get_event_loop()
    extractor = PDFExtractor()
    result = await loop.run_in_executor(None, extractor.extract, file_path)
    return result.text

