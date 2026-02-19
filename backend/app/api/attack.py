"""
MITRE ATT&CK API router.

Endpoints:
  GET  /api/v1/attack/tactics               – list all tactics
  GET  /api/v1/attack/tactics/{id}/techniques – techniques for a tactic
  GET  /api/v1/attack/techniques/search     – search techniques
  GET  /api/v1/attack/sync-status           – last sync metadata
  POST /api/v1/attack/sync                  – trigger a data sync

Per-threat attack endpoints:
  GET  /api/v1/attack/threats/{threat_id}/mappings         – list mappings
  POST /api/v1/attack/threats/{threat_id}/mappings         – add manual mapping
  POST /api/v1/attack/threats/{threat_id}/auto-map         – AI auto-map
  DELETE /api/v1/attack/threats/{threat_id}/mappings/{tid} – remove mapping
  GET  /api/v1/attack/threats/{threat_id}/kill-chains      – list kill chains
  POST /api/v1/attack/threats/{threat_id}/kill-chains      – generate kill chain
  DELETE /api/v1/attack/kill-chains/{kc_id}                – delete kill chain
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import (
    AttackTacticRead,
    AttackTechniqueRead,
    AttackTechniqueSummary,
    AttackSyncStatusRead,
    ThreatAttackMappingCreate,
    ThreatAttackMappingRead,
    AutoMapRequest,
    AutoMapResponse,
    KillChainRead,
    KillChainGenerateRequest,
)
from ..services.attack_data_service import attack_data_service
from ..services.taxii_sync_service import taxii_sync_service
from ..services.threat_attack_service import threat_attack_service
from ..services.kill_chain_service import kill_chain_service
from ..models.models import AttackTactic

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID"),
) -> tuple[UUID, UUID]:
    return x_tenant_id, x_user_id


# ─────────────────────────────────────────────────────────────────
# ATT&CK reference data
# ─────────────────────────────────────────────────────────────────

@router.get("/tactics", response_model=List[AttackTacticRead])
def list_tactics(
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List all cached ATT&CK tactics, ordered by MITRE ID."""
    tactics = attack_data_service.get_all_tactics(db)
    technique_counts = attack_data_service.get_tactic_technique_counts(db)

    # Attach technique_count to each tactic before returning
    result = []
    for t in tactics:
        read = AttackTacticRead.model_validate(t)
        read.technique_count = technique_counts.get(str(t.id), 0)
        result.append(read)
    return result


@router.get("/tactics/{tactic_id}/techniques", response_model=List[AttackTechniqueRead])
def list_techniques_for_tactic(
    tactic_id: UUID,
    include_subtechniques: bool = Query(False, description="Include sub-techniques"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List ATT&CK techniques for a specific tactic."""
    techniques = attack_data_service.get_techniques_by_tactic(
        db, tactic_id, include_subtechniques=include_subtechniques
    )
    return techniques


@router.get("/techniques/search", response_model=List[AttackTechniqueSummary])
def search_techniques(
    q: str = Query(..., min_length=2, description="Search keyword"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Full-text search across ATT&CK technique names and descriptions."""
    return attack_data_service.search_techniques(db, q, limit=limit)


@router.get("/techniques/{technique_id}", response_model=AttackTechniqueRead)
def get_technique(
    technique_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Get a single ATT&CK technique by its local DB ID."""
    technique = attack_data_service.get_technique(db, technique_id)
    if not technique:
        raise HTTPException(status_code=404, detail=f"Technique {technique_id} not found")
    return technique


# ─────────────────────────────────────────────────────────────────
# Sync
# ─────────────────────────────────────────────────────────────────

@router.get("/sync-status", response_model=AttackSyncStatusRead)
def get_sync_status(
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Return the status and metadata of the last ATT&CK sync."""
    record = attack_data_service.get_sync_status(db)
    if not record:
        return AttackSyncStatusRead(
            sync_status="never",
            tactics_count=0,
            techniques_count=0,
        )
    return record


@router.post("/sync", response_model=AttackSyncStatusRead)
def trigger_sync(
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """
    Trigger a full MITRE ATT&CK data sync.

    Downloads tactics and techniques from MITRE and caches them locally.
    This can take 30-60 seconds on first run.  Subsequent runs are faster
    due to upsert logic.
    """
    result = taxii_sync_service.sync(db)
    if result["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ATT&CK sync failed: {result.get('error_message', 'unknown error')}",
        )
    record = attack_data_service.get_sync_status(db)
    return record


# ─────────────────────────────────────────────────────────────────
# Threat ↔ Technique mappings
# ─────────────────────────────────────────────────────────────────

@router.get("/threats/{threat_id}/mappings", response_model=List[ThreatAttackMappingRead])
def list_threat_mappings(
    threat_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List all ATT&CK technique mappings for a threat."""
    return threat_attack_service.get_mappings(db, threat_id)


@router.post(
    "/threats/{threat_id}/mappings",
    response_model=ThreatAttackMappingRead,
    status_code=status.HTTP_201_CREATED,
)
def add_threat_mapping(
    threat_id: UUID,
    payload: ThreatAttackMappingCreate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Manually map a threat to an ATT&CK technique."""
    _, user_id = context
    try:
        mapping = threat_attack_service.add_mapping(
            db=db,
            threat_id=threat_id,
            technique_id=payload.technique_id,
            confidence_score=payload.confidence_score or 70,
            mapping_rationale=payload.mapping_rationale,
            auto_mapped=False,
            created_by_id=user_id,
        )
        return mapping
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/threats/{threat_id}/auto-map", response_model=AutoMapResponse)
def auto_map_threat(
    threat_id: UUID,
    payload: AutoMapRequest = AutoMapRequest(),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """
    Use AI (Bedrock) to automatically suggest and map ATT&CK techniques.

    Returns a list of suggestions.  Suggestions above the confidence threshold
    are automatically saved as mappings (set save_suggestions=false to skip).
    """
    tenant_id, _ = context
    try:
        result = threat_attack_service.auto_map_threat(
            db=db,
            threat_id=threat_id,
            tenant_id=tenant_id,
            save_suggestions=payload.save_suggestions,
            confidence_threshold=payload.confidence_threshold,
        )
        return AutoMapResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/threats/{threat_id}/mappings/{technique_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_threat_mapping(
    threat_id: UUID,
    technique_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Remove a specific ATT&CK technique mapping from a threat."""
    deleted = threat_attack_service.remove_mapping(db, threat_id, technique_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")


# ─────────────────────────────────────────────────────────────────
# Kill chains
# ─────────────────────────────────────────────────────────────────

@router.get("/threats/{threat_id}/kill-chains", response_model=List[KillChainRead])
def list_kill_chains(
    threat_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List all AI-generated kill chain scenarios for a threat."""
    return kill_chain_service.get_kill_chains(db, threat_id)


@router.post(
    "/threats/{threat_id}/kill-chains",
    response_model=KillChainRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_kill_chain(
    threat_id: UUID,
    payload: KillChainGenerateRequest = KillChainGenerateRequest(),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """
    Generate a new AI attack kill chain scenario for a threat.

    The scenario is built using the threat's mapped ATT&CK techniques and
    assessment context.  Each scenario is persisted and can be retrieved later.
    """
    tenant_id, _ = context
    try:
        kc = kill_chain_service.generate(
            db=db,
            threat_id=threat_id,
            tenant_id=tenant_id,
            threat_actor=payload.threat_actor,
            include_detection_hints=payload.include_detection_hints,
        )
        return kc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/kill-chains/{kill_chain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kill_chain(
    kill_chain_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Delete a specific kill chain scenario."""
    tenant_id, _ = context
    deleted = kill_chain_service.delete_kill_chain(db, kill_chain_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Kill chain not found")
