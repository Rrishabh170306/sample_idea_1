from __future__ import annotations
from typing import Any
from sqlalchemy.orm import Session
from app.db.models import UserProfile, UserDocument, ReviewQueue

class ProfileCRUD:
    def __init__(self, db: Session):
        self.db = db
        
    def get_profile(self, user_id: str) -> UserProfile | None:
        return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
    def create_or_update_profile(self, user_id: str, profile_data: dict[str, Any]) -> UserProfile:
        profile = self.get_profile(user_id)
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            
        for key, value in profile_data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
                
        self.db.commit()
        self.db.refresh(profile)
        return profile

class DocumentCRUD:
    def __init__(self, db: Session):
        self.db = db
        
    def create_document(self, doc_id: str, user_id: str, doc_type: str, file_path: str, data: dict, verified: bool) -> UserDocument:
        doc = UserDocument(
            id=doc_id,
            user_id=user_id,
            document_type=doc_type,
            file_path=file_path,
            extracted_data=data,
            verified=verified
        )
        self.db.add(doc)
        self.db.commit()
        return doc

class ReviewQueueCRUD:
    def __init__(self, db: Session):
        self.db = db
        
    def push_to_queue(self, queue_id: str, query: str, response: str, confidence: float, reason: str, session_id: str | None = None) -> ReviewQueue:
        item = ReviewQueue(
            id=queue_id,
            session_id=session_id,
            query=query,
            response=response,
            confidence=confidence,
            reason=reason,
            status="pending"
        )
        self.db.add(item)
        self.db.commit()
        return item
