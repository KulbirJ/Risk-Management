"""Threat Intelligence Enrichment API — Phase 1 Dual-Track endpoints."""
import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import (
    ThreatEnrichRequest,
    ThreatEnrichResponse,
    EnrichmentSummary,
    ThreatIntelEnrichmentRead,
    AttackGroupRead,
)
from ..services.intel.enrichment_orchestrator import EnrichmentOrchestrator
from ..services.intel.sector_frequency_service import SectorFrequencyService
from ..models.models import ThreatIntelEnrichment, AttackGroup, Threat

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared instances
_orchestrator = EnrichmentOrchestrator()
_sector_service = SectorFrequencyService()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID"),
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


# ──────────────────────────────────────────────────────
# Enrichment endpoints
# ──────────────────────────────────────────────────────

@router.post("/enrich", response_model=ThreatEnrichResponse)
async def enrich_threats(
    body: ThreatEnrichRequest,
    db: Session = Depends(get_db),
    context: tuple = Depends(get_tenant_context),
):
    """
    Run dual-track enrichment on selected threats or all threats in an assessment.
    
    Track A (CVE-based): NVD, CISA KEV, OTX by CVE, GitHub PoC
    Track B (Non-CVE): ATT&CK Groups, OTX by technique, Sector Frequency
    """
    tenant_id, user_id = context

    result = await _orchestrator.enrich_threats(
        db=db,
        tenant_id=tenant_id,
        threat_ids=body.threat_ids,
        assessment_id=body.assessment_id,
        force_refresh=body.force_refresh,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return ThreatEnrichResponse(**result)


@router.get("/threats/{threat_id}/summary", response_model=EnrichmentSummary)
async def get_threat_enrichment_summary(
    threat_id: UUID,
    db: Session = Depends(get_db),
    context: tuple = Depends(get_tenant_context),
):
    """Get the combined enrichment summary for a single threat."""
    tenant_id, user_id = context

    summary = await _orchestrator.get_enrichment_summary(db, tenant_id, threat_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Threat not found or not enriched")

    return summary


@router.get("/threats/{threat_id}/enrichments")
def list_threat_enrichments(
    threat_id: UUID,
    db: Session = Depends(get_db),
    context: tuple = Depends(get_tenant_context),
):
    """List all enrichment records for a threat, grouped by source."""
    tenant_id, user_id = context

    # Verify threat belongs to tenant
    threat = db.query(Threat).filter(
        Threat.id == threat_id,
        Threat.tenant_id == tenant_id,
    ).first()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    enrichments = (
        db.query(ThreatIntelEnrichment)
        .filter(ThreatIntelEnrichment.threat_id == threat_id)
        .order_by(ThreatIntelEnrichment.fetched_at.desc())
        .all()
    )

    return {
        "threat_id": str(threat_id),
        "enrichment_count": len(enrichments),
        "enrichments": [
            {
                "id": str(e.id),
                "source": e.source,
                "source_id": e.source_id,
                "severity_score": e.severity_score,
                "feature_vector": e.feature_vector,
                "fetched_at": e.fetched_at.isoformat() if e.fetched_at else None,  # type: ignore[union-attr]
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,  # type: ignore[union-attr]
                "is_stale": e.is_stale,
            }
            for e in enrichments
        ],
    }


# ──────────────────────────────────────────────────────
# Sector frequency endpoints
# ──────────────────────────────────────────────────────

@router.get("/sectors")
def list_sectors():
    """List all available industry sectors for threat frequency lookup."""
    return {"sectors": _sector_service.get_all_sectors()}


@router.get("/sectors/{sector}/frequency")
def get_sector_frequency(
    sector: str,
    catalogue_key: str = Query(..., description="Threat catalogue key, e.g. 'ransomware'"),
):
    """Look up annualised threat frequency for a sector + threat type."""
    result = _sector_service.get_frequency(sector, catalogue_key)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No frequency data for sector='{sector}', catalogue_key='{catalogue_key}'"
        )
    return result


# ──────────────────────────────────────────────────────
# ATT&CK Groups endpoints
# ──────────────────────────────────────────────────────

@router.get("/attack-groups")
def list_attack_groups(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by name or alias"),
    sector: Optional[str] = Query(None, description="Filter by target sector"),
    skip: int = 0,
    limit: int = 50,
):
    """List ATT&CK threat groups with optional filtering."""
    query = db.query(AttackGroup)

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(AttackGroup.name.ilike(search_lower))

    groups = query.order_by(AttackGroup.name).offset(skip).limit(limit).all()

    # Post-filter by sector if needed (JSONB array)
    if sector:
        sector_lower = sector.lower()
        groups = [g for g in groups if sector_lower in [s.lower() for s in (g.target_sectors or [])]]

    return {
        "count": len(groups),
        "groups": [
            {
                "id": str(g.id),
                "name": g.name,
                "aliases": g.aliases or [],
                "description": (g.description or "")[:300],
                "technique_count": len(list(g.technique_ids or [])),  # type: ignore[arg-type]
                "target_sectors": g.target_sectors or [],
                "first_seen": g.first_seen,
                "last_seen": g.last_seen,
                "url": g.url,
            }
            for g in groups
        ],
    }


@router.get("/attack-groups/{group_id}")
def get_attack_group(
    group_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details of a single ATT&CK group."""
    group = db.query(AttackGroup).filter(AttackGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Attack group not found")

    return {
        "id": str(group.id),
        "stix_id": group.stix_id,
        "name": group.name,
        "aliases": group.aliases or [],
        "description": group.description,
        "technique_ids": group.technique_ids or [],
        "target_sectors": group.target_sectors or [],
        "first_seen": group.first_seen,
        "last_seen": group.last_seen,
        "url": group.url,
    }
