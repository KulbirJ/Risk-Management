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
    industry_sector: Optional[str] = None  # e.g., "finance", "healthcare", "government"


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
    industry_sector: Optional[str] = None


class AssessmentRead(AssessmentBase):
    id: UUID
    status: str
    industry_sector: Optional[str] = None
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
    detected_by: Optional[str] = None


class ThreatRead(ThreatBase):
    id: UUID
    assessment_id: UUID
    catalogue_key: Optional[str] = None
    severity: str
    status: str
    cvss_score: Optional[str] = None
    detected_by: str
    intel_enriched: bool = False
    likelihood_score: int = 0
    likelihood_score_rationale: Optional[dict] = None
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
    upload_method: str = "PUT"  # "PUT" = presigned PUT (recommended); "POST" = legacy multipart


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
    document_type_confidence: Optional[int] = None
    quality: Optional[str] = None
    analysis_summary: Optional[str] = None
    analysis_findings: Optional[list] = None
    risk_indicators: Optional[dict] = None
    last_enriched_at: Optional[datetime] = None
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
    score_locked: bool = False


class ActiveRiskUpdate(BaseModel):
    title: Optional[str] = None
    residual_risk: Optional[str] = None
    mitigation_plan: Optional[str] = None
    status: Optional[str] = None
    risk_status: Optional[str] = None
    review_cycle_days: Optional[int] = None
    score_locked: Optional[bool] = None


class ActiveRiskOutcomeUpdate(BaseModel):
    """Record real-world outcome — feeds ground-truth labels into ML training."""
    outcome: str
    # materialized_breach | materialized_incident | mitigated_successfully
    # | accepted_no_incident | expired_unresolved
    outcome_severity: Optional[str] = None  # none | minor | moderate | major | critical
    false_positive: Optional[bool] = None
    days_to_resolution: Optional[int] = None


class ActiveRiskRead(ActiveRiskBase):
    id: UUID
    assessment_id: UUID
    threat_id: UUID
    risk_owner_id: Optional[UUID] = None
    review_cycle_days: Optional[int] = 30
    next_review_date: Optional[datetime] = None
    estimated_persistence_days: Optional[int] = None
    score_locked: bool = False
    status: str
    acceptance_date: Optional[datetime] = None
    detected_by: Optional[str] = None
    ai_rationale: Optional[str] = None
    risk_score: Optional[int] = None
    likelihood: Optional[int] = None
    impact: Optional[int] = None
    # Outcome tracking fields
    outcome: Optional[str] = None
    outcome_recorded_at: Optional[datetime] = None
    outcome_severity: Optional[str] = None
    days_to_resolution: Optional[int] = None
    false_positive: Optional[bool] = False
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


# ─────────────────────────────────────────────────────────────────
# MITRE ATT&CK Schemas
# ─────────────────────────────────────────────────────────────────

class AttackTacticRead(BaseModel):
    id: UUID
    stix_id: str
    mitre_id: str
    name: str
    shortname: str
    description: Optional[str] = None
    url: Optional[str] = None
    phase_order: Optional[int] = None
    technique_count: Optional[int] = None

    class Config:
        from_attributes = True


class AttackTechniqueRead(BaseModel):
    id: UUID
    stix_id: str
    mitre_id: str
    name: str
    tactic_id: Optional[UUID] = None
    tactic_shortname: Optional[str] = None
    description: Optional[str] = None
    detection_text: Optional[str] = None
    platforms: List[str] = []
    data_sources: List[str] = []
    mitigations: List[str] = []
    url: Optional[str] = None
    is_subtechnique: bool = False
    is_deprecated: bool = False

    class Config:
        from_attributes = True


class AttackTechniqueSummary(BaseModel):
    """Lightweight technique summary for dropdowns / suggestions."""
    id: UUID
    mitre_id: str
    name: str
    tactic_shortname: Optional[str] = None
    is_subtechnique: bool = False

    class Config:
        from_attributes = True


# Threat ↔ ATT&CK mapping schemas
class ThreatAttackMappingCreate(BaseModel):
    technique_id: UUID
    confidence_score: Optional[int] = 70    # 0-100
    mapping_rationale: Optional[str] = None
    auto_mapped: bool = False


class ThreatAttackMappingRead(BaseModel):
    id: UUID
    threat_id: UUID
    technique_id: UUID
    technique: AttackTechniqueRead
    confidence_score: int
    auto_mapped: bool
    mapping_rationale: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AutoMapRequest(BaseModel):
    """Request body to trigger auto-mapping for a threat."""
    save_suggestions: bool = True          # Auto-save suggestions above threshold
    confidence_threshold: int = 60         # 0-100


class AutoMapSuggestion(BaseModel):
    """Single auto-mapping suggestion from AI."""
    technique_id: Optional[UUID] = None
    mitre_id: str
    technique_name: str
    confidence_score: int
    mapping_rationale: str
    tactic_shortname: Optional[str] = None


class AutoMapResponse(BaseModel):
    suggestions: List[AutoMapSuggestion]
    saved_count: int
    threat_id: UUID


# Kill chain schemas
class KillChainStageRead(BaseModel):
    id: UUID
    stage_number: int
    tactic_name: str
    technique_id: Optional[UUID] = None
    technique_name: Optional[str] = None
    mitre_id: Optional[str] = None
    description: Optional[str] = None
    actor_behavior: Optional[str] = None
    detection_hint: Optional[str] = None

    class Config:
        from_attributes = True


class KillChainRead(BaseModel):
    id: UUID
    threat_id: UUID
    tenant_id: UUID
    scenario_name: str
    description: Optional[str] = None
    threat_actor: Optional[str] = None
    generated_by_ai: bool
    model_id: Optional[str] = None
    status: str = "complete"  # building | complete | failed
    stages: List[KillChainStageRead] = []
    created_at: datetime

    class Config:
        from_attributes = True


class KillChainGenerateRequest(BaseModel):
    """Optional parameters passed when generating a kill chain."""
    threat_actor: Optional[str] = None     # e.g. "APT29", leave blank for generic
    include_detection_hints: bool = True


# Sync status schema
class AttackSyncStatusRead(BaseModel):
    id: Optional[UUID] = None
    sync_status: str
    last_synced_at: Optional[datetime] = None
    tactics_count: int = 0
    techniques_count: int = 0
    source_url: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────
# Threat Intelligence Enrichment Schemas (Phase 1)
# ─────────────────────────────────────────────────────────────────

class ThreatIntelEnrichmentRead(BaseModel):
    """Read schema for a single enrichment record."""
    id: UUID
    threat_id: UUID
    source: str          # nvd, cisa_kev, otx_cve, otx_technique, github_poc, sector_freq, attack_group
    source_id: Optional[str] = None
    raw_data: Optional[dict] = None
    feature_vector: Optional[dict] = None
    severity_score: Optional[int] = None
    fetched_at: datetime
    expires_at: Optional[datetime] = None
    is_stale: bool = False

    class Config:
        from_attributes = True


class ThreatEnrichRequest(BaseModel):
    """Request to run dual-track enrichment on specific threats or a whole assessment."""
    assessment_id: Optional[UUID] = None   # Enrich all threats in assessment
    threat_ids: Optional[List[UUID]] = None  # Or specific threats
    force_refresh: bool = False            # Ignore cache TTL


class ThreatEnrichResponse(BaseModel):
    """Response from the enrichment orchestrator."""
    threats_enriched: int = 0
    enrichments_created: int = 0
    enrichments_updated: int = 0
    errors: List[str] = []
    feature_summary: Optional[dict] = None  # Aggregated feature stats


class EnrichmentSummary(BaseModel):
    """Combined enrichment summary for a single threat."""
    threat_id: UUID
    threat_title: str
    intel_enriched: bool
    likelihood_score: int
    sources: List[str] = []                # Which feeds returned data
    feature_vector: Optional[dict] = None  # Unified feature vector
    cve_data: Optional[dict] = None        # NVD + KEV combined
    otx_data: Optional[dict] = None        # OTX pulse data
    exploit_data: Optional[dict] = None    # GitHub PoC data
    sector_frequency: Optional[dict] = None  # Sector incident frequency
    attack_groups: Optional[List[dict]] = None  # Related threat groups
    enriched_at: Optional[datetime] = None


class AttackGroupRead(BaseModel):
    """Read schema for MITRE ATT&CK Groups."""
    id: UUID
    stix_id: str
    name: str
    aliases: List[str] = []
    description: Optional[str] = None
    technique_ids: List[str] = []
    target_sectors: List[str] = []
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    url: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────
# ML Scoring Schemas (Phase 2)
# ─────────────────────────────────────────────────────────────────

class MLScoreResult(BaseModel):
    """ML scoring result for a single threat."""
    threat_id: UUID
    ml_likelihood_score: int
    ml_likelihood_label: str  # low, medium, high, critical
    explanation: Optional[dict] = None
    model_info: Optional[dict] = None


class MLBatchScoreResult(BaseModel):
    """Batch scoring summary."""
    scored: int
    skipped_locked: int
    skipped_no_features: int
    total: int
    results: List[dict] = []


class MLModelInfo(BaseModel):
    """Model metadata."""
    trained: bool
    algorithm: str
    trained_at: Optional[str] = None
    training_samples: int = 0
    feature_count: int = 0
    feature_keys: List[str] = []
    metrics: Optional[dict] = None


class MLExplanation(BaseModel):
    """Feature-level explanation for a threat's score."""
    threat_id: UUID
    threat_title: str
    likelihood_score: int
    method: str  # model_feature_importance or rule_based_decomposition
    top_factors: Optional[List[dict]] = None
    components: Optional[List[dict]] = None
    all_factors: Optional[List[dict]] = None
    model_algorithm: Optional[str] = None


class BiasReport(BaseModel):
    """Sector-level score distribution report."""
    sectors: dict = {}
    total_threats: int = 0
    generated_at: Optional[str] = None


# ─────────────────────────────────────────────────────────────────
# Survival Analysis Schemas (Phase 2)
# ─────────────────────────────────────────────────────────────────

class SurvivalEstimateResult(BaseModel):
    """Persistence estimate for an active risk."""
    active_risk_id: UUID
    threat_id: UUID
    estimated_persistence_days: int
    sector: str
    residual_risk: str


class SurvivalCurve(BaseModel):
    """Survival curve data."""
    method: str
    sector: Optional[str] = None
    median_survival_days: Optional[float] = None
    timeline_days: List[float] = []
    survival_probability: List[float] = []
    n_observations: int = 0
    n_events: int = 0


# ─────────────────────────────────────────────────────────────────
# Graph Schemas (Phase 3)
# ─────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """A node in the threat knowledge graph."""
    id: str
    type: str  # threat, technique, tactic, group, cve
    label: str
    pagerank: float = 0.0
    betweenness: float = 0.0
    degree: float = 0.0


class GraphEdge(BaseModel):
    """An edge in the threat knowledge graph."""
    source: str
    target: str
    type: str  # uses_technique, belongs_to_tactic, has_cve


class AssessmentGraph(BaseModel):
    """Full knowledge graph for an assessment."""
    assessment_id: str
    nodes: List[dict] = []
    edges: List[dict] = []
    pagerank: dict = {}
    stats: dict = {}


class CriticalNode(BaseModel):
    """A node identified as critical by PageRank + betweenness."""
    id: str
    type: str
    label: str
    composite_score: float
    pagerank: float
    betweenness: float


# ─────────────────────────────────────────────────────────────────
# Clustering Schemas (Phase 4)
# ─────────────────────────────────────────────────────────────────

class ThreatCluster(BaseModel):
    """A cluster of similar threats."""
    cluster_id: int
    label: str
    size: int
    avg_likelihood_score: float
    dominant_features: List[dict] = []
    members: List[dict] = []


class ClusterResult(BaseModel):
    """Assessment clustering result."""
    assessment_id: Optional[str] = None
    clusters: List[dict] = []
    outliers: List[dict] = []
    quality: dict = {}
    threats: List[dict] = []
    parameters: Optional[dict] = None


class SimilarThreat(BaseModel):
    """A threat similar to a target threat."""
    threat_id: UUID
    title: str
    assessment_id: UUID
    likelihood_score: int
    similarity: float


# ─────────────────────────────────────────────────────────────────
# Report Schemas (Assessment + Per-Threat Report)
# ─────────────────────────────────────────────────────────────────

class KillChainStageReport(BaseModel):
    stage_number: int
    tactic_name: str
    technique_name: Optional[str] = None
    mitre_id: Optional[str] = None
    actor_behavior: Optional[str] = None
    detection_hint: Optional[str] = None


class KillChainReport(BaseModel):
    id: str
    scenario_name: str
    threat_actor: Optional[str] = None
    description: Optional[str] = None
    stages: List[KillChainStageReport] = []


class AttackMappingReport(BaseModel):
    mitre_id: str
    technique_name: str
    tactic_shortname: Optional[str] = None
    confidence_score: int
    mapping_rationale: Optional[str] = None


class ThreatReportItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    catalogue_key: Optional[str] = None
    cve_ids: List[str] = []
    cvss_score: Optional[str] = None
    likelihood: str
    impact: str
    severity: str
    status: str
    likelihood_score: int
    likelihood_label: str
    top_factors: List[dict] = []          # from likelihood_score_rationale
    intel_sources: List[str] = []         # which enrichment sources fired
    cve_data: dict = {}                   # NVD + CISA KEV
    otx_data: dict = {}                   # OTX pulses
    exploit_data: dict = {}               # GitHub PoC
    sector_frequency: dict = {}           # annualised sector frequency
    attack_groups: List[dict] = []        # related threat groups
    attack_mappings: List[AttackMappingReport] = []
    kill_chains: List[KillChainReport] = []
    recommendations: List[dict] = []


class AssessmentReportStats(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    mitigated: int = 0
    at_risk: int = 0
    enriched: int = 0
    with_exploits: int = 0
    with_kill_chains: int = 0


class AssessmentReportResponse(BaseModel):
    assessment_id: str
    assessment_title: str
    assessment_description: Optional[str] = None
    industry_sector: Optional[str] = None
    overall_impact: str
    generated_at: str
    stats: AssessmentReportStats
    top_risks: List[ThreatReportItem] = []   # top 5 by likelihood_score desc
    threats: List[ThreatReportItem] = []     # all threats, sorted critical → low


# ═══ Compliance Framework schemas ═══════════════════════════════════════════

class ComplianceFrameworkBase(BaseModel):
    key: str
    name: str
    version: Optional[str] = None
    description: Optional[str] = None

class ComplianceFrameworkCreate(ComplianceFrameworkBase):
    pass

class ComplianceFrameworkRead(ComplianceFrameworkBase):
    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    control_count: Optional[int] = None

    class Config:
        from_attributes = True


class ComplianceControlBase(BaseModel):
    control_id: str
    title: str
    description: Optional[str] = None
    family: Optional[str] = None
    priority: Optional[str] = None

class ComplianceControlCreate(ComplianceControlBase):
    framework_id: UUID

class ComplianceControlRead(ComplianceControlBase):
    id: UUID
    tenant_id: UUID
    framework_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceMappingBase(BaseModel):
    control_id: UUID
    threat_id: Optional[UUID] = None
    assessment_id: Optional[UUID] = None
    status: Optional[str] = "not_assessed"
    notes: Optional[str] = None
    evidence_ids: Optional[list] = []
    mapped_by: Optional[str] = "manual"
    confidence_score: Optional[int] = None

class ComplianceMappingCreate(ComplianceMappingBase):
    pass

class ComplianceMappingUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    evidence_ids: Optional[list] = None

class ComplianceMappingRead(ComplianceMappingBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    control_detail: Optional[ComplianceControlRead] = None

    class Config:
        from_attributes = True


class ComplianceSummary(BaseModel):
    """Per-framework compliance posture summary."""
    framework_id: str
    framework_name: str
    framework_key: str
    total_controls: int = 0
    mapped_controls: int = 0
    compliant: int = 0
    non_compliant: int = 0
    partially_compliant: int = 0
    not_applicable: int = 0
    not_assessed: int = 0
    compliance_pct: float = 0.0


# ─────────────────────────────────────────────────────────────────
# Supply Chain Risk Assessment Schemas (CCCS ITSAP.10.070)
# ─────────────────────────────────────────────────────────────────

class SupplyChainAssessmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    scope: Optional[str] = None
    industry_sector: Optional[str] = None
    # Step 1 — Technology Sensitivity
    technology_sensitivity: str = "Medium"  # Low | Medium | High
    technology_function: Optional[str] = None
    data_classification: Optional[str] = None
    ecosystem_importance: Optional[str] = None
    # Step 3 — Deployment context
    deployment_environment: Optional[str] = None
    cyber_defense_level: str = "Medium"  # Low | Medium | High
    deployment_notes: Optional[str] = None


class SupplyChainAssessmentCreate(SupplyChainAssessmentBase):
    pass


class SupplyChainAssessmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    industry_sector: Optional[str] = None
    status: Optional[str] = None
    technology_sensitivity: Optional[str] = None
    technology_function: Optional[str] = None
    data_classification: Optional[str] = None
    ecosystem_importance: Optional[str] = None
    deployment_environment: Optional[str] = None
    cyber_defense_level: Optional[str] = None
    deployment_notes: Optional[str] = None
    sbom_format: Optional[str] = None


class SupplyChainAssessmentRead(SupplyChainAssessmentBase):
    id: UUID
    tenant_id: UUID
    owner_user_id: UUID
    status: str
    overall_risk_score: Optional[int] = None
    overall_risk_level: Optional[str] = None
    sbom_uploaded: bool = False
    sbom_format: Optional[str] = None
    sbom_parsed_at: Optional[datetime] = None
    vendor_count: Optional[int] = 0
    dependency_count: Optional[int] = 0
    critical_dependency_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────
# Supply Chain Vendor Schemas (CCCS Step 2 — Supplier Confidence)
# ─────────────────────────────────────────────────────────────────

class SupplyChainVendorBase(BaseModel):
    name: str
    website: Optional[str] = None
    vendor_type: Optional[str] = None       # oss | commercial | internal | saas | paas | iaas
    country_of_origin: Optional[str] = None
    # Step 2 sub-factors
    foci_risk: str = "Low"                  # Low | Medium | High
    geopolitical_risk: str = "Low"          # Low | Medium | High
    business_practices_risk: str = "Low"    # Low | Medium | High
    security_certifications: Optional[List[str]] = []
    data_protection_maturity: str = "Medium"   # Low | Medium | High
    vuln_mgmt_maturity: str = "Medium"
    security_policies_maturity: str = "Medium"
    notes: Optional[str] = None


class SupplyChainVendorCreate(SupplyChainVendorBase):
    assessment_id: UUID


class SupplyChainVendorUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    vendor_type: Optional[str] = None
    country_of_origin: Optional[str] = None
    foci_risk: Optional[str] = None
    geopolitical_risk: Optional[str] = None
    business_practices_risk: Optional[str] = None
    security_certifications: Optional[List[str]] = None
    data_protection_maturity: Optional[str] = None
    vuln_mgmt_maturity: Optional[str] = None
    security_policies_maturity: Optional[str] = None
    notes: Optional[str] = None


class SupplyChainVendorRead(SupplyChainVendorBase):
    id: UUID
    tenant_id: UUID
    assessment_id: UUID
    supplier_confidence_level: Optional[str] = None   # High | Medium | Low
    supplier_risk_score: Optional[int] = None          # 0-100
    dependency_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────
# Supply Chain Dependency Schemas (SBOM components / CVE enrichment)
# ─────────────────────────────────────────────────────────────────

class SupplyChainDependencyBase(BaseModel):
    name: str
    version: Optional[str] = None
    package_type: Optional[str] = None     # npm | pip | maven | nuget | gem | go | cargo | container
    source: str = "direct"                 # direct | transitive
    license: Optional[str] = None
    repository_url: Optional[str] = None
    notes: Optional[str] = None


class SupplyChainDependencyCreate(SupplyChainDependencyBase):
    assessment_id: UUID
    vendor_id: Optional[UUID] = None
    cve_ids: Optional[List[str]] = []
    cvss_score: Optional[float] = None


class SupplyChainDependencyUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    package_type: Optional[str] = None
    source: Optional[str] = None
    license: Optional[str] = None
    vendor_id: Optional[UUID] = None
    cve_ids: Optional[List[str]] = None
    cvss_score: Optional[float] = None
    notes: Optional[str] = None


class SupplyChainDependencyRead(SupplyChainDependencyBase):
    id: UUID
    tenant_id: UUID
    assessment_id: UUID
    vendor_id: Optional[UUID] = None
    sbom_source: Optional[str] = None
    cve_ids: List[str] = []
    cvss_score: Optional[float] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    ml_enriched: bool = False
    enriched_at: Optional[datetime] = None
    is_in_cisa_kev: bool = False
    has_public_poc: bool = False
    has_patch: bool = False
    epss_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────
# SBOM + Scoring Schemas
# ─────────────────────────────────────────────────────────────────

class SBOMParseRequest(BaseModel):
    """SBOM content to parse (CycloneDX JSON or SPDX JSON)."""
    sbom_content: dict        # Raw parsed SBOM JSON
    sbom_format: str = "cyclonedx"   # cyclonedx | spdx


class SBOMParseResponse(BaseModel):
    """Dependencies extracted from an SBOM."""
    format_detected: str
    component_count: int
    components: List[SupplyChainDependencyCreate]
    warnings: List[str] = []


class SCRiskScoreResponse(BaseModel):
    """Recalculated overall risk score for a supply chain assessment."""
    assessment_id: UUID
    technology_sensitivity: str
    avg_supplier_risk: float
    deployment_risk: str
    overall_risk_score: int
    overall_risk_level: str
    vendor_scores: List[dict] = []
    dependency_critical_count: int = 0


class SCEnrichDependenciesRequest(BaseModel):
    """Request to run ML enrichment on all unenriched dependencies."""
    dependency_ids: Optional[List[UUID]] = None  # None = enrich all unenriched


class SCEnrichDependenciesResponse(BaseModel):
    enriched: int
    skipped: int
    errors: List[str] = []
    gap_controls: int = 0
