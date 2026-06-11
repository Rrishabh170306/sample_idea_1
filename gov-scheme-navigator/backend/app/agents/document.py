from __future__ import annotations

import uuid
from app.agents.state import AgentState
from app.document_intel.classifier import classify_document
from app.document_intel.extractor import extract_entities
import logging

logger = logging.getLogger(__name__)

class DocumentAgent:
    def __init__(self, doc_crud=None, review_crud=None):
        self.doc_crud = doc_crud
        self.review_crud = review_crud

    def process(self, state: AgentState) -> dict:
        profile = state.get("user_profile", {})
        user_id = profile.get("user_id", "default-user")
        
        doc_text = state.get("query", "") or ""

        try:
            doc_type = classify_document(doc_text)
            extraction_result = extract_entities(doc_text, doc_type)
            extracted_data = extraction_result.get("extracted_data", {})
            confidence = float(extraction_result.get("confidence", 0.0))
        except Exception as exc:
            logger.exception("Document processing failed for user %s: %s", user_id, exc)
            return {"user_profile": profile, "confidence_score": 0.0, "needs_human_review": True}

        verified = confidence >= 0.8
        
        if self.doc_crud:
            self.doc_crud.create_document(
                doc_id=str(uuid.uuid4()),
                user_id=user_id,
                doc_type=doc_type,
                file_path="/mock/path/doc.pdf",
                data=extracted_data,
                verified=verified
            )
            
        if not verified and self.review_crud:
            self.review_crud.push_to_queue(
                queue_id=str(uuid.uuid4()),
                query=doc_text,
                response=str(extracted_data),
                confidence=confidence,
                reason=f"Low confidence ({confidence}) extracting {doc_type}"
            )
            
        updated_profile = profile.copy()
        if verified:
            updated_profile.update(extracted_data)
            updated_profile["document_verified"] = True
            
        return {
            "user_profile": updated_profile,
            "confidence_score": confidence,
            "needs_human_review": not verified
        }
