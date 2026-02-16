"""Pydantic schemas for API requests/responses."""
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# Tenant schemas
class TenantBase(BaseModel):
    name: str


class TenantCreate(TenantBase):
    pass


class TenantRead(TenantBase):
    id: UUID
    region: str
    created_at: datetime

    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None


class UserCreate(UserBase):
    password: Optional[str] = None  # Optional for Cognito SSO


class UserRead(UserBase):
    id: UUID
    roles: List[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Assessment schemas
class AssessmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    system_background: Optional[str] = None
    scope: Optional[str] = None
    tech_stack: Optional[List[str]] = []
    overall_impact: str = "Medium"


class AssessmentCreate(AssessmentBase):
    pass


class AssessmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    system_background: Optional[str] = None
    scope: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    overall_impact: Optional[str] = None
    status: Optional[str] = None


class AssessmentRead(AssessmentBase):
    id: UUID
    status: str
    owner_user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Threat schemas
class ThreatBase(BaseModel):
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    cve_ids: Optional[List[str]] = []
    likelihood: str = "Medium"
    impact: str = "Medium"
    status: str = "identified"


class ThreatCreate(ThreatBase):
    catalogue_key: Optional[str] = None
    detected_by: str = "manual"
    cvss_score: Optional[str] = None


class ThreatPatch(BaseModel):
    title: Optional[str] = None
    likelihood: Optional[str] = None
    impact: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    status: Optional[str] = None


class ThreatRead(ThreatBase):
    id: UUID
    assessment_id: UUID
    catalogue_key: Optional[str] = None
    severity: str
    status: str
    cvss_score: Optional[str] = None
    detected_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Evidence schemas
class EvidenceInitRequest(BaseModel):
    file_name: str
    content_type: str
    size_bytes: int
    threat_id: Optional[UUID] = None
    document_type: Optional[str] = None  # vulnerability_scan, architecture_doc, policy, other


class EvidenceInitResponse(BaseModel):
    """Response from initiating an upload - contains presigned URL for direct S3 upload."""
    evidence_id: UUID
    upload_url: str
    upload_fields: dict
    s3_key: str


class EvidenceComplete(BaseModel):
    """Request to mark upload as complete after S3 upload finishes."""
    pass


class EvidenceRead(BaseModel):
    id: UUID
    assessment_id: UUID
    threat_id: Optional[UUID] = None
    uploaded_by_id: Optional[UUID] = None
    file_name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    s3_key: Optional[str] = None
    status: str = "processing"
    extracted_text: Optional[str] = None
    extract_metadata: Optional[dict] = None
    document_type: Optional[str] = None
    quality: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Recommendation schemas
class RecommendationBase(BaseModel):
    text: str
    type: str = "remediation"
    priority: str = "Medium"


class RecommendationCreate(RecommendationBase):
    threat_id: Optional[UUID] = None
    assessment_id: UUID
    owner_user_id: Optional[UUID] = None
    target_date: Optional[datetime] = None


class RecommendationUpdate(BaseModel):
    text: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    owner_user_id: Optional[UUID] = None


class RecommendationRead(RecommendationBase):
    id: UUID
    threat_id: Optional[UUID] = None
    status: str
    owner_user_id: Optional[UUID] = None
    target_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Active Risk schemas
class ActiveRiskBase(BaseModel):
    title: Optional[str] = None
    residual_risk: str = "Medium"
    mitigation_plan: Optional[str] = None
    risk_status: str = "Planned"


class ActiveRiskCreate(ActiveRiskBase):
    threat_id: UUID
    risk_owner_id: UUID
    review_cycle_days: int = 30


class ActiveRiskUpdate(BaseModel):
    title: Optional[str] = None
    residual_risk: Optional[str] = None
    mitigation_plan: Optional[str] = None
    status: Optional[str] = None
    risk_status: Optional[str] = None
    review_cycle_days: Optional[int] = None


class ActiveRiskRead(ActiveRiskBase):
    id: UUID
    assessment_id: UUID
    threat_id: UUID
    risk_owner_id: Optional[UUID] = None
    review_cycle_days: Optional[int] = 30
    status: str
    acceptance_date: Optional[datetime] = None
    detected_by: Optional[str] = None
    ai_rationale: Optional[str] = None
    risk_score: Optional[int] = None
    likelihood: Optional[int] = None
    impact: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Threat Catalogue schemas
class ThreatCatalogueBase(BaseModel):
    catalogue_key: str
    title: str
    description: Optional[str] = None
    default_likelihood: str = "Medium"
    default_impact: str = "Medium"
    mitigations: Optional[List[str]] = []


class ThreatCatalogueRead(ThreatCatalogueBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Audit Log schemas
class AuditLogRead(BaseModel):
    id: UUID
    actor_user_id: Optional[UUID] = None
    action_type: str
    resource_type: str
    resource_id: str
    changes: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Intelligence schemas
class IntelligenceEnrichRequest(BaseModel):
    """Request to enrich an assessment with AI analysis."""
    assessment_id: UUID
    job_type: str = "full_enrichment"  # full_enrichment, vulnerability_scan, threat_mapping


class IntelligenceEnrichResponse(BaseModel):
    """Response from an enrichment job."""
    job_id: UUID
    assessment_id: UUID
    status: str
    vulnerabilities_identified: int = 0
    threats_mapped: int = 0
    risks_created: int = 0
    recommendations_generated: int = 0
    errors: List[str] = []
    model_used: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class IntelligenceJobRead(BaseModel):
    """Read schema for intelligence jobs."""
    id: UUID
    assessment_id: UUID
    initiated_by_id: UUID
    status: str
    job_type: str
    model_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IntelligenceStatusResponse(BaseModel):
    """Status check for the intelligence service."""
    bedrock_enabled: bool
    primary_model: str
    fallback_model: str
    bedrock_region: str
    confidence_threshold: float
