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


class EvidenceComplete(BaseModel):
    s3_etag: str


class EvidenceRead(BaseModel):
    id: UUID
    assessment_id: UUID
    threat_id: Optional[UUID] = None
    file_name: str
    mime_type: str
    size_bytes: Optional[int] = None
    status: str
    quality: str
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
    title: str
    residual_risk: str = "Medium"
    mitigation_plan: Optional[str] = None
    risk_status: str = "Planned"


class ActiveRiskCreate(ActiveRiskBase):
    threat_id: UUID
    risk_owner_id: UUID
    review_cycle_days: int = 30


class ActiveRiskUpdate(BaseModel):
    residual_risk: Optional[str] = None
    mitigation_plan: Optional[str] = None
    status: Optional[str] = None
    risk_status: Optional[str] = None


class ActiveRiskRead(ActiveRiskBase):
    id: UUID
    threat_id: UUID
    risk_owner_id: UUID
    status: str
    acceptance_date: Optional[datetime] = None
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
