"""MCP Document Server — exposes document analysis as MCP tools."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class ExtractDocumentTool:
    """MCP tool: extract structured data from a document file."""

    name = "extract_document"
    description = (
        "Extract structured information from an uploaded document (Aadhaar, PAN, income certificate, etc.). "
        "Returns extracted fields and verification status."
    )

    async def run(
        self,
        file_path: str,
        document_type: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Args:
            file_path: Absolute path to the uploaded file
            document_type: Type of document (aadhaar, pan, income_certificate, land_record, etc.)
            user_id: Optional user ID to store extraction results against

        Returns:
            Dict with extracted fields, verified status, and confidence
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        extracted: dict[str, Any] = {}
        confidence = 0.0

        try:
            from app.document_intel.ocr import OCRProcessor
            processor = OCRProcessor()
            raw_text = await processor.extract_text(file_path)
            extracted["raw_text"] = raw_text[:500]  # Store truncated
        except Exception as exc:
            logger.warning("OCR extraction failed: %s", exc)
            raw_text = ""

        # Use LLM to parse the OCR text into structured fields
        if raw_text:
            try:
                extracted.update(
                    await self._llm_parse_document(raw_text, document_type)
                )
                confidence = 0.8
            except Exception as exc:
                logger.warning("LLM document parsing failed: %s", exc)
                confidence = 0.4

        verified = confidence >= 0.6

        # Persist to DB if user_id provided
        if user_id:
            try:
                await self._store_document(
                    user_id=user_id,
                    document_type=document_type,
                    file_path=file_path,
                    extracted_data=extracted,
                    verified=verified,
                )
            except Exception as exc:
                logger.warning("Failed to store document record: %s", exc)

        return {
            "document_type": document_type,
            "extracted": extracted,
            "verified": verified,
            "confidence": confidence,
        }

    async def _llm_parse_document(
        self, raw_text: str, document_type: str
    ) -> dict[str, Any]:
        """Use LLM to parse OCR text into structured fields."""
        from app.llm.client import LLMClient

        prompt = f"""\
Extract structured information from this {document_type} document text.
Return ONLY valid JSON with relevant fields.

Document type: {document_type}
Document text:
{raw_text[:2000]}

For Aadhaar: extract name, dob, gender, address, aadhaar_number (last 4 digits only)
For PAN: extract name, pan_number, dob
For income_certificate: extract name, annual_income, issuing_authority, date
For land_record: extract owner_name, survey_number, area_hectares, district, state

Return JSON object with extracted fields only.
"""
        client = LLMClient()
        response = client.generate_sync(prompt, temperature=0.0, max_tokens=512)

        # Extract JSON from response
        import json
        import re
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}

    async def _store_document(
        self,
        user_id: str,
        document_type: str,
        file_path: str,
        extracted_data: dict[str, Any],
        verified: bool,
    ) -> None:
        from app.db.session import get_db
        from app.db.models import UserDocument

        doc_id = str(uuid.uuid4())
        async with get_db() as session:
            doc = UserDocument(
                id=doc_id,
                user_id=user_id,
                document_type=document_type,
                file_path=file_path,
                extracted_data=extracted_data,
                verified=verified,
            )
            session.add(doc)
            await session.commit()
        logger.info("Stored document %s for user %s", doc_id, user_id)


class ListDocumentsTool:
    """MCP tool: list documents uploaded by a user."""

    name = "list_user_documents"
    description = "List all documents uploaded and processed for a given user."

    async def run(self, user_id: str) -> dict[str, Any]:
        try:
            from app.db.session import get_db
            from app.db.models import UserDocument
            from sqlalchemy import select

            async with get_db() as session:
                result = await session.execute(
                    select(UserDocument).where(UserDocument.user_id == user_id)
                )
                docs = result.scalars().all()
                return {
                    "user_id": user_id,
                    "documents": [
                        {
                            "id": d.id,
                            "document_type": d.document_type,
                            "verified": d.verified,
                            "uploaded_at": d.uploaded_at.isoformat()
                            if d.uploaded_at else None,
                        }
                        for d in docs
                    ],
                    "total": len(docs),
                }
        except Exception as exc:
            logger.exception("ListDocumentsTool failed: %s", exc)
            return {"error": str(exc)}


class DocumentMCPServer:
    """MCP server exposing document extraction tools."""

    def __init__(self):
        self.tools = {
            ExtractDocumentTool.name: ExtractDocumentTool(),
            ListDocumentsTool.name: ListDocumentsTool(),
        }

    async def handle(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(tool_name)
        if tool is None:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return await tool.run(**params)
        except Exception as exc:
            logger.exception("MCP tool %s failed: %s", tool_name, exc)
            return {"error": str(exc)}

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": t.name, "description": t.description}
            for t in self.tools.values()
        ]
