"""SQLAlchemy models for Phase 0 MVP."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, UUID, ForeignKey, Integer, Enum, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum
from ..db.database import Base


class Tenant(Base):
    """Multi-tenant organization."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    region = Column(String(50), default="ca-west-1")
    settings = Column(JSONB, default={})  # retention, consent flags, etc.
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant")
    assessments = relationship("Assessment", back_populates="tenant")


class User(Base):
    """User account (single-tenant per user initially)."""
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255))
    cognito_sub = Column(String(255), nullable=True)  # Cognito user ID
    roles = Column(JSONB, default=["viewer"])  # ["admin", "assessor", "reviewer", "risk_owner", "auditor", "viewer"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    assessments = relationship("Assessment", back_populates="owner")
    threats = relationship("Threat", back_populates="created_by_user")
    evidence = relationship("Evidence", back_populates="uploaded_by_user")
    audit_logs = relationship("AuditLog", back_populates="actor")


class Assessment(Base):
    """Security assessment record."""
    __tablename__ = "assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    system_background = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    tech_stack = Column(JSONB, default=[])  # ["Python", "PostgreSQL", "AWS"]
    overall_impact = Column(String(20), default="Medium")  # Low, Medium, High, Critical
    status = Column(String(20), default="draft")  # draft, in_review, completed, archived
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="assessments")
    owner = relationship("User", back_populates="assessments")
    threats = relationship("Threat", back_populates="assessment", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="assessment", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="assessment", cascade="all, delete-orphan")
    active_risks = relationship("ActiveRisk", back_populates="assessment", cascade="all, delete-orphan")


class Threat(Base):
    """Identified or catalogued threat."""
    __tablename__ = "threats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True)
    catalogue_key = Column(String(255), nullable=True, index=True)  # Reference to threat catalogue
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    detected_by = Column(String(50), default="manual")  # scan, diagram, manual, ai
    cve_ids = Column(JSONB, default=[])  # ["CVE-2023-1234", ...]
    cvss_score = Column(String(10), nullable=True)  # e.g., "7.5"
    likelihood = Column(String(20), default="Medium")  # Low, Medium, High, Critical
    likelihood_score = Column(Integer, default=0)  # 0-100 (future use for Phase 1)
    impact = Column(String(20), default="Medium")  # Low, Medium, High, Critical
    severity = Column(String(20), default="Medium")  # Low, Medium, High, Critical (computed)
    status = Column(String(20), default="identified")  # identified, in_review, at_risk, mitigated
    ai_rationale = Column(Text, nullable=True)  # (future use for Phase 1 — AI explanation)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="threats")
    created_by_user = relationship("User", back_populates="threats")
    evidence = relationship("Evidence", back_populates="threat")
    recommendations = relationship("Recommendation", back_populates="threat")
    active_risk = relationship("ActiveRisk", back_populates="threat", uselist=False)


class Evidence(Base):
    """Uploaded evidence files (diagrams, scans, docs)."""
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True)
    threat_id = Column(UUID(as_uuid=True), ForeignKey("threats.id"), nullable=True)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    s3_key = Column(String(512), nullable=False)  # S3 object key
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=True)
    status = Column(String(50), default="processing")  # processing, ready, failed
    extracted_text = Column(Text, nullable=True)  # Extracted text content from document
    extract_metadata = Column(JSONB, nullable=True)  # Parsing metadata (page count, etc.)
    document_type = Column(String(50), nullable=True)  # vulnerability_scan, architecture_doc, policy, other
    quality = Column(String(20), default="medium")  # high, medium, low
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="evidence")
    threat = relationship("Threat", back_populates="evidence")
    uploaded_by_user = relationship("User", back_populates="evidence")


class Recommendation(Base):
    """Mitigation or remediation recommendations."""
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=True)
    threat_id = Column(UUID(as_uuid=True), ForeignKey("threats.id"), nullable=True)
    active_risk_id = Column(UUID(as_uuid=True), ForeignKey("active_risks.id"), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    text = Column(Text, nullable=True)  # Deprecated, use description
    type = Column(String(50), default="remediation")  # mitigation, remediation, compensating
    priority = Column(String(20), default="Medium")  # Low, Medium, High, Critical
    status = Column(String(50), default="open")  # open, in_progress, done, accepted
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_date = Column(DateTime(timezone=True), nullable=True)
    confidence_score = Column(Integer, default=0)  # 0-100 (AI confidence)
    ai_generated = Column(Boolean, default=False)
    estimated_effort = Column(String(20), nullable=True)  # low, medium, high
    cost_estimate = Column(String(20), nullable=True)  # low, medium, high
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="recommendations")
    threat = relationship("Threat", back_populates="recommendations")


class ActiveRisk(Base):
    """Active risk register for non-fixable threats."""
    __tablename__ = "active_risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)
    threat_id = Column(UUID(as_uuid=True), ForeignKey("threats.id"), nullable=False)
    title = Column(String(255), nullable=True)
    risk_score = Column(Integer, default=50)  # 0-100 calculated risk score
    likelihood = Column(Integer, default=5)  # 1-10 probability score
    impact = Column(Integer, default=5)  # 1-10 impact score
    residual_risk = Column(String(20), default="Medium")  # Low, Medium, High, Critical
    risk_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    mitigation_plan = Column(Text, nullable=True)
    acceptance_date = Column(DateTime(timezone=True), nullable=True)
    review_cycle_days = Column(Integer, default=30)
    status = Column(String(50), default="open")  # open, accepted, mitigating, closed
    risk_status = Column(String(50), default="Planned")  # Planned, Ongoing, Delayed, Completed, Accepted
    detected_by = Column(String(50), default="manual")  # manual, ai_intelligence
    ai_rationale = Column(Text, nullable=True)  # AI explanation for risk score
    extra_data = Column(JSONB, default={})  # Additional risk metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="active_risks")
    threat = relationship("Threat", back_populates="active_risk")


class AuditLog(Base):
    """Immutable audit trail of all mutations."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action_type = Column(String(255), nullable=False)  # e.g., "assessment.create", "threat.update"
    resource_type = Column(String(100), nullable=False)  # Assessment, Threat, etc.
    resource_id = Column(String(255), nullable=False)
    changes = Column(JSONB, nullable=True)  # {before: {...}, after: {...}} or delta
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    actor = relationship("User", back_populates="audit_logs")


class ThreatCatalogue(Base):
    """Reference catalogue of threat types (canonical)."""
    __tablename__ = "threat_catalogue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    catalogue_key = Column(String(255), nullable=False, unique=True)  # e.g., "malicious_code"
    name = Column(String(255), nullable=False)  # Display name
    title = Column(String(255), nullable=True)  # Alias for name
    category = Column(String(100), nullable=True)  # Threat category (e.g., "Network", "Application", "Physical")
    description = Column(Text, nullable=True)
    default_likelihood = Column(String(20), default="Medium")  # default likelihood
    default_impact = Column(String(20), default="Medium")  # default impact
    mitigations = Column(JSONB, default=[])  # List of suggested mitigations
    is_active = Column(Boolean, default=True)  # Active threats shown in intelligence mapping
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IntelligenceJob(Base):
    """Track AI enrichment jobs for assessments."""
    __tablename__ = "intelligence_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True)
    initiated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    job_type = Column(String(50), default="full_enrichment")  # full_enrichment, vulnerability_scan, threat_mapping, etc.
    model_id = Column(String(255), nullable=True)  # Bedrock model used
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    results = Column(JSONB, nullable=True)  # {vulnerabilities_found: 5, threats_mapped: 8, ...}
    extra_data = Column(JSONB, default={})  # Additional job metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
