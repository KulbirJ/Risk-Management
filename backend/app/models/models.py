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
    industry_sector = Column(String(50), nullable=True)  # e.g., "finance", "healthcare", "government"
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
    intel_enriched = Column(Boolean, default=False)  # True when threat intel enrichment has run
    likelihood_score_rationale = Column(JSONB, default={})  # Feature vector / explanation for likelihood_score
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
    attack_mappings = relationship("ThreatAttackMapping", back_populates="threat", cascade="all, delete-orphan")
    kill_chains = relationship("KillChain", back_populates="threat", cascade="all, delete-orphan")


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
    last_enriched_at = Column(DateTime(timezone=True), nullable=True)  # When this file was last included in AI enrichment
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
    next_review_date = Column(DateTime(timezone=True), nullable=True)  # Computed: created_at + review_cycle_days
    estimated_persistence_days = Column(Integer, nullable=True)  # Survival-analysis output
    score_locked = Column(Boolean, default=False)  # When True, ML cannot override risk_score
    status = Column(String(50), default="open")  # open, accepted, mitigating, closed
    risk_status = Column(String(50), default="Planned")  # Planned, Ongoing, Delayed, Completed, Accepted
    detected_by = Column(String(50), default="manual")  # manual, ai_intelligence
    ai_rationale = Column(Text, nullable=True)  # AI explanation for risk score
    extra_data = Column(JSONB, default={})  # Additional risk metadata
    # Outcome tracking — feeds real-world labels back into ML training (Stage 1)
    outcome = Column(String(50), nullable=True)
    # Values: materialized_breach, materialized_incident, mitigated_successfully,
    #         accepted_no_incident, expired_unresolved
    outcome_recorded_at = Column(DateTime(timezone=True), nullable=True)
    outcome_severity = Column(String(20), nullable=True)  # none, minor, moderate, major, critical
    days_to_resolution = Column(Integer, nullable=True)   # actual days open — survival ground truth
    false_positive = Column(Boolean, default=False)        # risk owner: "this was never real"
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

# ─────────────────────────────────────────────────────────────────
# MITRE ATT&CK Integration Models
# ─────────────────────────────────────────────────────────────────

# Canonical ATT&CK tactic ordering (Enterprise, follows kill chain phase flow)
ATTACK_TACTIC_ORDER: dict[str, int] = {
    "reconnaissance":       1,
    "resource-development": 2,
    "initial-access":       3,
    "execution":            4,
    "persistence":          5,
    "privilege-escalation": 6,
    "defense-evasion":      7,
    "credential-access":    8,
    "discovery":            9,
    "lateral-movement":     10,
    "collection":           11,
    "command-and-control":  12,
    "exfiltration":         13,
    "impact":               14,
}


class AttackTactic(Base):
    """MITRE ATT&CK Tactic (e.g., Initial Access, Execution, Persistence)."""
    __tablename__ = "attack_tactics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    stix_id = Column(String(255), unique=True, nullable=False)      # stix id from MITRE
    mitre_id = Column(String(50), nullable=False, index=True)        # e.g. "TA0001"
    name = Column(String(255), nullable=False)                       # e.g. "Initial Access"
    shortname = Column(String(100), nullable=False, index=True)      # e.g. "initial-access"
    description = Column(Text, nullable=True)
    url = Column(String(512), nullable=True)
    phase_order = Column(Integer, nullable=True, index=True)         # 1-14 canonical kill chain order
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    techniques = relationship("AttackTechnique", back_populates="tactic")


class AttackTechnique(Base):
    """MITRE ATT&CK Technique or Sub-technique (e.g., Phishing T1566)."""
    __tablename__ = "attack_techniques"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    stix_id = Column(String(255), unique=True, nullable=False)       # stix id from MITRE
    mitre_id = Column(String(50), nullable=False, index=True)        # e.g. "T1566" or "T1566.001"
    name = Column(String(255), nullable=False)                       # e.g. "Phishing"
    tactic_id = Column(UUID(as_uuid=True), ForeignKey("attack_tactics.id"), nullable=True, index=True)
    tactic_shortname = Column(String(100), nullable=True)            # denormalized for fast lookups
    description = Column(Text, nullable=True)
    platforms = Column(JSONB, default=[])                            # ["Windows", "Linux", "macOS", ...]
    data_sources = Column(JSONB, default=[])                         # ["Email logs", ...]
    mitigations = Column(JSONB, default=[])                          # cached mitigation texts
    url = Column(String(512), nullable=True)
    is_subtechnique = Column(Boolean, default=False)
    parent_technique_id = Column(UUID(as_uuid=True), ForeignKey("attack_techniques.id"), nullable=True)
    detection_text = Column(Text, nullable=True)                     # x_mitre_detection from STIX
    is_deprecated = Column(Boolean, default=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    tactic = relationship("AttackTactic", back_populates="techniques")
    threat_mappings = relationship("ThreatAttackMapping", back_populates="technique")
    subtechniques = relationship("AttackTechnique",
                                  primaryjoin="AttackTechnique.parent_technique_id == AttackTechnique.id",
                                  foreign_keys="[AttackTechnique.parent_technique_id]",
                                  lazy="select")


class ThreatAttackMapping(Base):
    """Junction table linking a Threat record to one or more ATT&CK Techniques."""
    __tablename__ = "threat_attack_mappings"
    __table_args__ = (UniqueConstraint("threat_id", "technique_id", name="uq_threat_technique"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    threat_id = Column(UUID(as_uuid=True), ForeignKey("threats.id"), nullable=False, index=True)
    technique_id = Column(UUID(as_uuid=True), ForeignKey("attack_techniques.id"), nullable=False, index=True)
    confidence_score = Column(Integer, default=70)    # 0-100; AI sets this, user can adjust
    auto_mapped = Column(Boolean, default=False)      # True = AI suggestion, False = manual
    mapping_rationale = Column(Text, nullable=True)   # AI explanation or user note
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    threat = relationship("Threat", back_populates="attack_mappings")
    technique = relationship("AttackTechnique", back_populates="threat_mappings")
    created_by_user = relationship("User")


class KillChain(Base):
    """AI-generated attack scenario / kill chain for a specific threat."""
    __tablename__ = "kill_chains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    threat_id = Column(UUID(as_uuid=True), ForeignKey("threats.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    scenario_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    threat_actor = Column(String(255), nullable=True)    # e.g. "APT29", "Ransomware group"
    generated_by_ai = Column(Boolean, default=True)
    model_id = Column(String(255), nullable=True)
    # Status for async generation: building | complete | failed
    status = Column(String(50), default="complete", nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    threat = relationship("Threat", back_populates="kill_chains")
    stages = relationship("KillChainStage", back_populates="kill_chain",
                          cascade="all, delete-orphan",
                          order_by="KillChainStage.stage_number")


class KillChainStage(Base):
    """A single stage/step within an attack kill chain scenario."""
    __tablename__ = "kill_chain_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kill_chain_id = Column(UUID(as_uuid=True), ForeignKey("kill_chains.id"), nullable=False, index=True)
    technique_id = Column(UUID(as_uuid=True), ForeignKey("attack_techniques.id"), nullable=True)
    stage_number = Column(Integer, nullable=False)
    tactic_name = Column(String(100), nullable=False)    # e.g. "Initial Access"
    technique_name = Column(String(255), nullable=True)  # e.g. "Spearphishing Link"
    mitre_id = Column(String(50), nullable=True)         # e.g. "T1566.002"
    description = Column(Text, nullable=True)
    actor_behavior = Column(Text, nullable=True)         # What the attacker does
    detection_hint = Column(Text, nullable=True)         # How to detect this stage
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    kill_chain = relationship("KillChain", back_populates="stages")
    technique = relationship("AttackTechnique")


class AttackSyncStatus(Base):
    """Tracks the status and metadata of the last MITRE ATT&CK data sync."""
    __tablename__ = "attack_sync_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sync_status = Column(String(50), default="never")    # never, running, completed, failed
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    tactics_count = Column(Integer, default=0)
    techniques_count = Column(Integer, default=0)
    source_url = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ─────────────────────────────────────────────────────────────────
# Threat Intelligence Enrichment Models (Phase 1)
# ─────────────────────────────────────────────────────────────────

class ThreatIntelEnrichment(Base):
    """Cached enrichment data from external threat-intel feeds for a specific threat."""
    __tablename__ = "threat_intel_enrichments"
    __table_args__ = (
        UniqueConstraint("threat_id", "source", name="uq_threat_enrichment_source"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    threat_id = Column(UUID(as_uuid=True), ForeignKey("threats.id"), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # nvd, cisa_kev, otx_cve, otx_technique, github_poc, sector_freq, attack_group
    source_id = Column(String(255), nullable=True)  # CVE-2023-1234, T1566, etc.
    raw_data = Column(JSONB, default={})  # Full API response or extracted payload
    feature_vector = Column(JSONB, default={})  # Normalised numeric features for ML
    severity_score = Column(Integer, nullable=True)  # 0-100 normalised severity
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Cache TTL
    is_stale = Column(Boolean, default=False)

    # Relationships
    threat = relationship("Threat", backref="intel_enrichments")


class AttackGroup(Base):
    """MITRE ATT&CK Intrusion Set / Threat Group (e.g., APT29, FIN7)."""
    __tablename__ = "attack_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    stix_id = Column(String(255), unique=True, nullable=False)       # intrusion-set--<uuid>
    name = Column(String(255), nullable=False, index=True)           # e.g., "APT29"
    aliases = Column(JSONB, default=[])                              # ["Cozy Bear", "The Dukes"]
    description = Column(Text, nullable=True)
    technique_ids = Column(JSONB, default=[])                        # List of ATT&CK technique STIX IDs used
    target_sectors = Column(JSONB, default=[])                       # ["government", "finance", ...]
    first_seen = Column(String(50), nullable=True)
    last_seen = Column(String(50), nullable=True)
    url = Column(String(512), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # No FK to techniques — join via technique_ids JSONB array