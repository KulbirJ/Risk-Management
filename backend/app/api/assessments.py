"""Assessment API router endpoints."""
from datetime import datetime
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session, joinedload

from ..db.database import get_db
from ..schemas.schemas import (
    AssessmentCreate, AssessmentRead, AssessmentUpdate,
    AssessmentReportResponse, AssessmentReportStats,
    ThreatReportItem, AttackMappingReport, KillChainReport, KillChainStageReport,
)
from ..services.assessment_service import AssessmentService
from ..models.models import (
    Threat, ThreatIntelEnrichment, ThreatAttackMapping, AttackTechnique,
    KillChain, KillChainStage, Recommendation,
)

router = APIRouter()


# Dependency to extract tenant_id and user_id from headers
# In production, this would extract from validated JWT token
def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


@router.post("/", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment(
    assessment: AssessmentCreate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Create a new risk assessment.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID (must be active user in tenant)
    """
    tenant_id, user_id = context
    
    try:
        created_assessment = AssessmentService.create_assessment(
            db=db,
            assessment_data=assessment,
            tenant_id=tenant_id,
            user_id=user_id
        )
        return created_assessment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{assessment_id}", response_model=AssessmentRead)
def get_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get a specific assessment by ID.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    assessment = AssessmentService.get_assessment(
        db=db,
        assessment_id=assessment_id,
        tenant_id=tenant_id
    )
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment {assessment_id} not found"
        )
    
    return assessment


@router.get("/", response_model=List[AssessmentRead])
def list_assessments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (draft, in_review, completed, archived)"),
    owner_user_id: Optional[UUID] = Query(None, description="Filter by owner user ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of records to return"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    List all assessments for the tenant with optional filters.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    assessments = AssessmentService.list_assessments(
        db=db,
        tenant_id=tenant_id,
        status=status_filter,
        owner_user_id=owner_user_id,
        skip=skip,
        limit=limit
    )
    
    return assessments


@router.patch("/{assessment_id}", response_model=AssessmentRead)
def update_assessment(
    assessment_id: UUID,
    update_data: AssessmentUpdate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Update an existing assessment.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        updated_assessment = AssessmentService.update_assessment(
            db=db,
            assessment_id=assessment_id,
            tenant_id=tenant_id,
            update_data=update_data
        )
        
        if not updated_assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment {assessment_id} not found"
            )
        
        return updated_assessment
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Delete (archive) an assessment.
    
    This is a soft delete - the assessment status is changed to 'archived'.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        success = AssessmentService.delete_assessment(
            db=db,
            assessment_id=assessment_id,
            tenant_id=tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment {assessment_id} not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats/count", response_model=dict)
def get_assessment_stats(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get assessment statistics (count).
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    count = AssessmentService.get_assessment_count(
        db=db,
        tenant_id=tenant_id,
        status=status_filter
    )
    
    return {"count": count, "status_filter": status_filter}


# ─────────────────────────────────────────────────────────────────
# Report endpoint — aggregates all threat data in one call
# ─────────────────────────────────────────────────────────────────

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _likelihood_label(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


@router.get("/{assessment_id}/report", response_model=AssessmentReportResponse)
def get_assessment_report(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """
    Aggregated report for a single assessment — combines threat data,
    ML scores, intel enrichments, ATT&CK mappings, kill chains and
    recommendations into one response suitable for both CISO and
    technical audiences.
    """
    tenant_id, _ = context

    assessment = AssessmentService.get_assessment(
        db=db, assessment_id=assessment_id, tenant_id=tenant_id
    )
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")

    # ── 1. Load all threats for the assessment ──────────────────────
    threats = (
        db.query(Threat)
        .filter(Threat.assessment_id == assessment_id, Threat.tenant_id == tenant_id)
        .order_by(Threat.likelihood_score.desc())
        .all()
    )

    # ── 2. Bulk-load all related data keyed by threat_id ────────────
    threat_ids = [t.id for t in threats]

    # Intel enrichments
    enrichments = (
        db.query(ThreatIntelEnrichment)
        .filter(ThreatIntelEnrichment.threat_id.in_(threat_ids))
        .all()
    ) if threat_ids else []
    enrich_map: dict = {}   # threat_id → {source: raw_data}
    for e in enrichments:
        enrich_map.setdefault(str(e.threat_id), {})[str(e.source)] = e.raw_data or {}

    # ATT&CK mappings (with technique joined)
    mappings = (
        db.query(ThreatAttackMapping)
        .options(joinedload(ThreatAttackMapping.technique))
        .filter(ThreatAttackMapping.threat_id.in_(threat_ids))
        .all()
    ) if threat_ids else []
    mapping_map: dict = {}  # threat_id → [AttackMappingReport]
    for m in mappings:
        tech = m.technique
        if not tech:
            continue
        mapping_map.setdefault(str(m.threat_id), []).append(
            AttackMappingReport(
                mitre_id=tech.mitre_id,
                technique_name=tech.name,
                tactic_shortname=tech.tactic_shortname,
                confidence_score=m.confidence_score or 0,
                mapping_rationale=m.mapping_rationale,
            )
        )

    # Kill chains (with stages joined)
    kill_chains = (
        db.query(KillChain)
        .options(joinedload(KillChain.stages))
        .filter(
            KillChain.threat_id.in_(threat_ids),
            KillChain.status == "complete",
        )
        .all()
    ) if threat_ids else []
    kc_map: dict = {}  # threat_id → [KillChainReport]
    for kc in kill_chains:
        stages = sorted(kc.stages, key=lambda s: s.stage_number)
        kc_map.setdefault(str(kc.threat_id), []).append(
            KillChainReport(
                id=str(kc.id),
                scenario_name=kc.scenario_name,
                threat_actor=kc.threat_actor,
                description=kc.description,
                stages=[
                    KillChainStageReport(
                        stage_number=s.stage_number,
                        tactic_name=s.tactic_name,
                        technique_name=s.technique_name,
                        mitre_id=s.mitre_id,
                        actor_behavior=s.actor_behavior,
                        detection_hint=s.detection_hint,
                    )
                    for s in stages
                ],
            )
        )

    # Recommendations
    recs = (
        db.query(Recommendation)
        .filter(Recommendation.threat_id.in_(threat_ids))
        .all()
    ) if threat_ids else []
    rec_map: dict = {}  # threat_id → [dict]
    for r in recs:
        rec_map.setdefault(str(r.threat_id), []).append({
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "type": r.type,
            "priority": r.priority,
            "status": r.status,
        })

    # ── 3. Build per-threat report items ───────────────────────────
    threat_items: List[ThreatReportItem] = []
    stats = AssessmentReportStats()
    stats.total = len(threats)

    for t in threats:
        tid = str(t.id)
        sev = (t.severity or "medium").lower()
        st = (t.status or "identified").lower()

        # Stats counters
        if sev == "critical":
            stats.critical += 1
        elif sev == "high":
            stats.high += 1
        elif sev == "medium":
            stats.medium += 1
        else:
            stats.low += 1
        if st == "mitigated":
            stats.mitigated += 1
        if st == "at_risk":
            stats.at_risk += 1
        if t.intel_enriched:
            stats.enriched += 1

        # Extract intel data per source
        t_enrich = enrich_map.get(tid, {})
        cve_data = t_enrich.get("nvd", {})
        # Merge CISA KEV into cve_data
        cisa = t_enrich.get("cisa_kev", {})
        if cisa:
            cve_data = {**cve_data, "cisa_kev": cisa}
        otx_data = t_enrich.get("otx_cve", t_enrich.get("otx_technique", {}))
        exploit_data = t_enrich.get("github_poc", {})
        sector_frequency = t_enrich.get("sector_freq", {})
        attack_groups_raw = t_enrich.get("attack_group", {})

        if exploit_data:
            stats.with_exploits += 1

        t_kcs = kc_map.get(tid, [])
        if t_kcs:
            stats.with_kill_chains += 1

        # ML top factors from persisted rationale
        rationale = t.likelihood_score_rationale or {}
        top_factors = rationale.get("top_factors", [])

        score = t.likelihood_score or 0
        threat_items.append(
            ThreatReportItem(
                id=tid,
                title=t.title,
                description=t.description,
                recommendation=t.recommendation,
                catalogue_key=t.catalogue_key,
                cve_ids=list(t.cve_ids or []),
                cvss_score=t.cvss_score,
                likelihood=t.likelihood,
                impact=t.impact,
                severity=t.severity,
                status=t.status,
                likelihood_score=score,
                likelihood_label=_likelihood_label(score),
                top_factors=top_factors if isinstance(top_factors, list) else [],
                intel_sources=list(t_enrich.keys()),
                cve_data=cve_data,
                otx_data=otx_data,
                exploit_data=exploit_data,
                sector_frequency=sector_frequency,
                attack_groups=[attack_groups_raw] if attack_groups_raw else [],
                attack_mappings=mapping_map.get(tid, []),
                kill_chains=t_kcs,
                recommendations=rec_map.get(tid, []),
            )
        )

    # Sort critical → low by severity, then by score desc within tier
    threat_items.sort(key=lambda x: (_SEVERITY_ORDER.get(x.severity.lower(), 9), -x.likelihood_score))
    top_risks = sorted(threat_items, key=lambda x: -x.likelihood_score)[:5]

    return AssessmentReportResponse(
        assessment_id=str(assessment.id),
        assessment_title=assessment.title,
        assessment_description=assessment.description,
        industry_sector=assessment.industry_sector,
        overall_impact=assessment.overall_impact,
        generated_at=datetime.utcnow().isoformat() + "Z",
        stats=stats,
        top_risks=top_risks,
        threats=threat_items,
    )
