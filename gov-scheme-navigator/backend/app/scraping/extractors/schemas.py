from __future__ import annotations

from pydantic import BaseModel, Field


class BenefitSchema(BaseModel):
    type: str | None = None
    amount: float | None = None
    frequency: str | None = None
    installments: int | None = None
    description: str | None = None


class EligibilitySchema(BaseModel):
    age_min: int | None = None
    age_max: int | None = None
    income_max: float | None = None
    land_ownership_required: bool | None = None
    land_hectares_max: float | None = None
    occupation: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class SchemeSchema(BaseModel):
    scheme_id: str
    name: str
    name_hindi: str | None = None
    department: str | None = None
    ministry: str | None = None
    state: str | None = None
    category: list[str] = Field(default_factory=list)
    target_beneficiaries: list[str] = Field(default_factory=list)
    eligibility: EligibilitySchema = Field(default_factory=EligibilitySchema)
    benefits: BenefitSchema = Field(default_factory=BenefitSchema)
    documents_required: list[str] = Field(default_factory=list)
    application_process: list[str] = Field(default_factory=list)
    official_url: str | None = None
    status: str = "active"


class ExtractionResult(BaseModel):
    record: SchemeSchema
    confidence: float = 0.0
