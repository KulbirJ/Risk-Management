"""Compliance framework API router endpoints."""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import (
    ComplianceFrameworkCreate, ComplianceFrameworkRead,
    ComplianceControlCreate, ComplianceControlRead,
    ComplianceMappingCreate, ComplianceMappingUpdate, ComplianceMappingRead,
    ComplianceSummary,
)
from ..services import compliance_service
from ..services import compliance_mapping_engine

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID"),
) -> tuple[UUID, UUID]:
    return x_tenant_id, x_user_id


# ── Frameworks ──────────────────────────────────────────────────────────────

@router.get("/frameworks", response_model=List[ComplianceFrameworkRead])
def list_frameworks(
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List all active compliance frameworks for this tenant."""
    tenant_id, _ = context
    rows = compliance_service.list_frameworks(db, str(tenant_id))
    return rows


@router.get("/frameworks/{framework_id}", response_model=ComplianceFrameworkRead)
def get_framework(
    framework_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = context
    fw = compliance_service.get_framework(db, str(tenant_id), framework_id)
    if not fw:
        raise HTTPException(status_code=404, detail="Framework not found")
    return fw


@router.post("/frameworks", response_model=ComplianceFrameworkRead, status_code=201)
def create_framework(
    body: ComplianceFrameworkCreate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, user_id = context
    return compliance_service.create_framework(
        db, str(tenant_id), str(user_id), body.model_dump(),
    )


@router.post("/frameworks/seed")
def seed_frameworks(
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Seed NIST 800-53, ISO 27001, and CIS v8 frameworks + controls."""
    tenant_id, _ = context
    result = compliance_service.seed_frameworks(db, str(tenant_id))
    return {"status": "ok", **result}


# ── Controls ────────────────────────────────────────────────────────────────

@router.get("/frameworks/{framework_id}/controls", response_model=List[ComplianceControlRead])
def list_controls(
    framework_id: UUID,
    family: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = context
    return compliance_service.list_controls(
        db, str(tenant_id), framework_id, family=family, skip=skip, limit=limit,
    )


@router.post("/controls", response_model=ComplianceControlRead, status_code=201)
def create_control(
    body: ComplianceControlCreate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, user_id = context
    return compliance_service.create_control(
        db, str(tenant_id), str(user_id), body.model_dump(),
    )


# ── Mappings ────────────────────────────────────────────────────────────────

@router.get("/mappings", response_model=List[ComplianceMappingRead])
def list_mappings(
    assessment_id: Optional[UUID] = Query(None),
    framework_id: Optional[UUID] = Query(None),
    threat_id: Optional[UUID] = Query(None),
    mapping_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = context
    return compliance_service.list_mappings(
        db, str(tenant_id),
        assessment_id=assessment_id,
        framework_id=framework_id,
        threat_id=threat_id,
        status=mapping_status,
    )


@router.post("/mappings", response_model=ComplianceMappingRead, status_code=201)
def create_mapping(
    body: ComplianceMappingCreate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, user_id = context
    return compliance_service.create_mapping(
        db, str(tenant_id), str(user_id), body.model_dump(),
    )


@router.put("/mappings/{mapping_id}", response_model=ComplianceMappingRead)
def update_mapping(
    mapping_id: UUID,
    body: ComplianceMappingUpdate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, user_id = context
    mapping = compliance_service.update_mapping(
        db, str(tenant_id), str(user_id), mapping_id,
        body.model_dump(exclude_unset=True),
    )
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@router.delete("/mappings/{mapping_id}", status_code=204)
def delete_mapping(
    mapping_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, user_id = context
    if not compliance_service.delete_mapping(db, str(tenant_id), str(user_id), mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found")


# ── Summary ─────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=List[ComplianceSummary])
def compliance_summary(
    assessment_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Per-framework compliance posture summary."""
    tenant_id, _ = context
    return compliance_service.get_compliance_summary(
        db, str(tenant_id), assessment_id=assessment_id,
    )


# ── Auto-Mapping ────────────────────────────────────────────────────────────

@router.post("/auto-map")
def auto_map_compliance(
    threat_id: UUID = Query(..., description="Threat to auto-map"),
    framework_key: str = Query(..., description="Framework key (e.g. nist-800-53)"),
    assessment_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Run intelligent auto-mapping for a threat against a compliance framework."""
    tenant_id, user_id = context
    try:
        result = compliance_mapping_engine.run_auto_mapping(
            db=db,
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            threat_id=threat_id,
            framework_key=framework_key,
            assessment_id=assessment_id,
        )
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/seed-defaults")
def seed_defaults(
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Seed the static threat→control default mapping table."""
    tenant_id, _ = context
    result = compliance_service.seed_threat_control_defaults(db, str(tenant_id))
    return {"status": "ok", **result}


# ── Gap Analysis ────────────────────────────────────────────────────────────

@router.get("/gaps")
def compliance_gaps(
    framework_key: str = Query(..., description="Framework key"),
    assessment_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Return controls that are NOT mapped to any threat (compliance gaps)."""
    tenant_id, _ = context
    gaps = compliance_service.get_compliance_gaps(
        db, str(tenant_id), framework_key, assessment_id=assessment_id,
    )
    return gaps
