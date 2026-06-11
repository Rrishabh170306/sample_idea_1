from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Scheme(Base):
    __tablename__ = "schemes"

    scheme_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    name_hindi = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    ministry = Column(String(255), nullable=True)
    state = Column(String(64), nullable=True)
    category = Column(JSON, nullable=True)
    target_beneficiaries = Column(JSON, nullable=True)
    eligibility = Column(JSON, nullable=True)
    benefits = Column(JSON, nullable=True)
    documents_required = Column(JSON, nullable=True)
    application_process = Column(JSON, nullable=True)
    official_url = Column(String(500), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="active")
    last_updated = Column(DateTime(timezone=True), nullable=True)
    content_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String(36), primary_key=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)
    state = Column(String(50), nullable=True)
    district = Column(String(100), nullable=True)
    income = Column(Float, nullable=True)
    occupation = Column(String(100), nullable=True)
    category = Column(String(20), nullable=True)
    education = Column(String(50), nullable=True)
    disability_status = Column(Boolean, default=False)
    disability_type = Column(String(50), nullable=True)
    land_ownership = Column(Boolean, default=False)
    land_hectares = Column(Float, nullable=True)
    business_ownership = Column(Boolean, default=False)
    business_type = Column(String(50), nullable=True)
    marital_status = Column(String(20), nullable=True)
    dependents = Column(Integer, nullable=True)
    profile_completeness = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserDocument(Base):
    __tablename__ = "user_documents"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    document_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    extracted_data = Column(JSON, nullable=True)
    verified = Column(Boolean, default=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    messages = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    reason = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    reviewer_id = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SchemeChunk(Base):
    __tablename__ = "scheme_chunks"

    id = Column(String(36), primary_key=True)
    scheme_id = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    chunk_type = Column(String(20), nullable=True)
    parent_chunk_id = Column(String(36), nullable=True)
    embedding = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
