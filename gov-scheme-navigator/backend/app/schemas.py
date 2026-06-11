from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, constr


class BenefitModel(BaseModel):
    type: Optional[str]
    amount: Optional[float]
    frequency: Optional[str]
    installments: Optional[int]
    description: Optional[str]


class EligibilityModel(BaseModel):
    age_min: Optional[int]
    age_max: Optional[int]
    income_max: Optional[float]
    land_ownership_required: Optional[bool]
    land_hectares_max: Optional[float]
    occupation: Optional[List[str]] = []
    states: Optional[List[str]] = []
    exclusions: Optional[List[str]] = []


class SchemeSchema(BaseModel):
    scheme_id: constr(min_length=1, max_length=64)
    name: constr(min_length=1, max_length=255)
    name_hindi: Optional[constr(max_length=255)]
    department: Optional[str]
    ministry: Optional[str]
    state: Optional[str]
    category: Optional[List[str]] = []
    target_beneficiaries: Optional[List[str]] = []
    eligibility: Optional[EligibilityModel]
    benefits: Optional[BenefitModel]
    documents_required: Optional[List[str]] = []
    application_process: Optional[List[str]] = []
    official_url: Optional[HttpUrl]
    deadline: Optional[datetime]
    status: Optional[str] = "active"
    content_hash: Optional[str]
    source_urls: Optional[List[HttpUrl]] = []


class ChunkSchema(BaseModel):
    id: str
    scheme_id: str
    content: str
    chunk_type: Optional[str]
    parent_chunk_id: Optional[str]
    metadata: Optional[dict] = {}
    created_at: Optional[datetime]
