"""Supply Chain Risk Assessment API endpoints (CCCS ITSAP.10.070)."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import (
    SBOMParseRequest,
    SBOMParseResponse,
    SCEnrichDependenciesRequest,
    SCEnrichDependenciesResponse,
    SCRiskScoreResponse,
    SupplyChainAssessmentCreate,
    SupplyChainAssessmentRead,
    SupplyChainAssessmentUpdate,
    SupplyChainDependencyCreate,
    SupplyChainDependencyRead,
    SupplyChainDependencyUpdate,
    SupplyChainVendorCreate,
    SupplyChainVendorRead,
    SupplyChainVendorUpdate,
)
from ..services import supply_chain_service as svc

router = APIRouter()


# ── Auth helper ───────────────────────────────────────────────────────────────

def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID"),
) -> tuple[UUID, UUID]:
    return x_tenant_id, x_user_id


# ─────────────────────────────────────────────────────────────────────────────
# Assessments
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[SupplyChainAssessmentRead])
def list_assessments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List all supply chain assessments for the tenant."""
    tenant_id, _ = ctx
    return svc.list_assessments(db, tenant_id, skip=skip, limit=limit, status=status)


@router.post("/", response_model=SupplyChainAssessmentRead, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: SupplyChainAssessmentCreate,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Create a new supply chain risk assessment."""
    tenant_id, user_id = ctx
    return svc.create_assessment(db, tenant_id, user_id, payload)


@router.get("/{assessment_id}", response_model=SupplyChainAssessmentRead)
def get_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Get a single supply chain assessment."""
    tenant_id, _ = ctx
    obj = svc.get_assessment(db, tenant_id, assessment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return obj


@router.put("/{assessment_id}", response_model=SupplyChainAssessmentRead)
def update_assessment(
    assessment_id: UUID,
    payload: SupplyChainAssessmentUpdate,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Update a supply chain assessment."""
    tenant_id, _ = ctx
    obj = svc.get_assessment(db, tenant_id, assessment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return svc.update_assessment(db, obj, payload)


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Delete a supply chain assessment and all related data."""
    tenant_id, _ = ctx
    obj = svc.get_assessment(db, tenant_id, assessment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    svc.delete_assessment(db, obj)


# ─────────────────────────────────────────────────────────────────────────────
# Risk Scoring
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{assessment_id}/score", response_model=SCRiskScoreResponse)
def recalculate_score(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Recalculate the CCCS 3-step risk score for the assessment."""
    tenant_id, _ = ctx
    obj = svc.get_assessment(db, tenant_id, assessment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return svc.recalculate_risk_score(db, tenant_id, obj)


# ─────────────────────────────────────────────────────────────────────────────
# SBOM Parsing
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{assessment_id}/sbom/parse", response_model=SBOMParseResponse)
def parse_sbom(
    assessment_id: UUID,
    payload: SBOMParseRequest,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """
    Parse a CycloneDX or SPDX JSON SBOM and return extracted dependency objects.
    Call POST /{assessment_id}/dependencies/bulk to persist them.
    """
    tenant_id, _ = ctx
    obj = svc.get_assessment(db, tenant_id, assessment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    result = svc.parse_sbom(assessment_id, tenant_id, payload)

    # Mark assessment as having an SBOM uploaded
    from ..schemas.schemas import SupplyChainAssessmentUpdate
    from datetime import datetime, timezone
    obj.sbom_uploaded = True
    obj.sbom_format = result.format_detected
    obj.sbom_parsed_at = datetime.now(timezone.utc)
    db.commit()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Vendors
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{assessment_id}/vendors", response_model=List[SupplyChainVendorRead])
def list_vendors(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List all vendors (Step 2 — Supplier Confidence) for this assessment."""
    tenant_id, _ = ctx
    if not svc.get_assessment(db, tenant_id, assessment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return svc.list_vendors(db, tenant_id, assessment_id)


@router.post(
    "/{assessment_id}/vendors",
    response_model=SupplyChainVendorRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor(
    assessment_id: UUID,
    payload: SupplyChainVendorCreate,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Add a vendor and compute its Step 2 supplier confidence score."""
    tenant_id, _ = ctx
    if not svc.get_assessment(db, tenant_id, assessment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if payload.assessment_id != assessment_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="assessment_id in body must match path parameter",
        )
    return svc.create_vendor(db, tenant_id, payload)


@router.get("/{assessment_id}/vendors/{vendor_id}", response_model=SupplyChainVendorRead)
def get_vendor(
    assessment_id: UUID,
    vendor_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = ctx
    obj = svc.get_vendor(db, tenant_id, vendor_id)
    if not obj or obj.assessment_id != assessment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return obj


@router.put("/{assessment_id}/vendors/{vendor_id}", response_model=SupplyChainVendorRead)
def update_vendor(
    assessment_id: UUID,
    vendor_id: UUID,
    payload: SupplyChainVendorUpdate,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = ctx
    obj = svc.get_vendor(db, tenant_id, vendor_id)
    if not obj or obj.assessment_id != assessment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return svc.update_vendor(db, obj, payload)


@router.delete(
    "/{assessment_id}/vendors/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vendor(
    assessment_id: UUID,
    vendor_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = ctx
    obj = svc.get_vendor(db, tenant_id, vendor_id)
    if not obj or obj.assessment_id != assessment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    svc.delete_vendor(db, obj)


# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{assessment_id}/dependencies",
    response_model=List[SupplyChainDependencyRead],
)
def list_dependencies(
    assessment_id: UUID,
    vendor_id: Optional[UUID] = Query(None),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """List all software dependencies for this assessment."""
    tenant_id, _ = ctx
    if not svc.get_assessment(db, tenant_id, assessment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return svc.list_dependencies(db, tenant_id, assessment_id, vendor_id, risk_level)


@router.post(
    "/{assessment_id}/dependencies",
    response_model=SupplyChainDependencyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_dependency(
    assessment_id: UUID,
    payload: SupplyChainDependencyCreate,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Add a single software dependency."""
    tenant_id, _ = ctx
    if not svc.get_assessment(db, tenant_id, assessment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if payload.assessment_id != assessment_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="assessment_id in body must match path parameter",
        )
    return svc.create_dependency(db, tenant_id, payload)


@router.post(
    "/{assessment_id}/dependencies/bulk",
    response_model=List[SupplyChainDependencyRead],
    status_code=status.HTTP_201_CREATED,
)
def bulk_create_dependencies(
    assessment_id: UUID,
    payload: List[SupplyChainDependencyCreate],
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """Bulk-create dependencies — typically called after SBOM parsing."""
    tenant_id, _ = ctx
    if not svc.get_assessment(db, tenant_id, assessment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    results = []
    for dep in payload:
        dep.assessment_id = assessment_id
        results.append(svc.create_dependency(db, tenant_id, dep))
    return results


@router.get(
    "/{assessment_id}/dependencies/{dep_id}",
    response_model=SupplyChainDependencyRead,
)
def get_dependency(
    assessment_id: UUID,
    dep_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = ctx
    obj = svc.get_dependency(db, tenant_id, dep_id)
    if not obj or obj.assessment_id != assessment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found")
    return obj


@router.put(
    "/{assessment_id}/dependencies/{dep_id}",
    response_model=SupplyChainDependencyRead,
)
def update_dependency(
    assessment_id: UUID,
    dep_id: UUID,
    payload: SupplyChainDependencyUpdate,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = ctx
    obj = svc.get_dependency(db, tenant_id, dep_id)
    if not obj or obj.assessment_id != assessment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found")
    return svc.update_dependency(db, obj, payload)


@router.delete(
    "/{assessment_id}/dependencies/{dep_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_dependency(
    assessment_id: UUID,
    dep_id: UUID,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    tenant_id, _ = ctx
    obj = svc.get_dependency(db, tenant_id, dep_id)
    if not obj or obj.assessment_id != assessment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found")
    svc.delete_dependency(db, obj)


# ─────────────────────────────────────────────────────────────────────────────
# ML Enrichment
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{assessment_id}/dependencies/enrich",
    response_model=SCEnrichDependenciesResponse,
)
def enrich_dependencies(
    assessment_id: UUID,
    payload: SCEnrichDependenciesRequest,
    db: Session = Depends(get_db),
    ctx: tuple[UUID, UUID] = Depends(get_tenant_context),
):
    """
    Enrich unenriched dependencies via the ML microservice.
    Populates risk_score, is_in_cisa_kev, has_public_poc, epss_score.
    """
    tenant_id, _ = ctx
    if not svc.get_assessment(db, tenant_id, assessment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return svc.enrich_dependencies_with_ml(
        db, tenant_id, assessment_id, payload.dependency_ids
    )
