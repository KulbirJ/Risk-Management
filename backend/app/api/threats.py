"""Threat API router endpoints."""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import ThreatCreate, ThreatRead, ThreatPatch
from ..services.threat_service import ThreatService

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


@router.post("/", response_model=ThreatRead, status_code=status.HTTP_201_CREATED)
def create_threat(
    threat: ThreatCreate,
    assessment_id: UUID = Query(..., description="Assessment ID to link threat to"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Create a new threat for an assessment.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    
    Query parameters:
    - assessment_id: UUID of the assessment this threat belongs to
    """
    tenant_id, user_id = context
    
    try:
        created_threat = ThreatService.create_threat(
            db=db,
            threat_data=threat,
            assessment_id=assessment_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        return created_threat
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{threat_id}", response_model=ThreatRead)
def get_threat(
    threat_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get a specific threat by ID.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    threat = ThreatService.get_threat(
        db=db,
        threat_id=threat_id,
        tenant_id=tenant_id
    )
    
    if not threat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat {threat_id} not found"
        )
    
    return threat


@router.get("/", response_model=List[ThreatRead])
def list_threats(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (Low, Medium, High, Critical)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of records to return"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    List all threats for the tenant with optional filters.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    threats = ThreatService.list_threats(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        severity=severity,
        skip=skip,
        limit=limit
    )
    
    return threats


@router.patch("/{threat_id}", response_model=ThreatRead)
def update_threat(
    threat_id: UUID,
    update_data: ThreatPatch,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Update an existing threat (likelihood, impact, description).
    Severity is automatically recalculated.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        updated_threat = ThreatService.update_threat(
            db=db,
            threat_id=threat_id,
            tenant_id=tenant_id,
            update_data=update_data
        )
        
        if not updated_threat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Threat {threat_id} not found"
            )
        
        return updated_threat
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{threat_id}/promote", response_model=ThreatRead)
def promote_threat(
    threat_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Promote an AI-assessed threat to analyst-assessed.
    This protects it from being cleared on future AI enrichment runs.
    """
    tenant_id, _ = context

    threat = ThreatService.get_threat(db=db, threat_id=threat_id, tenant_id=tenant_id)
    if not threat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat {threat_id} not found"
        )

    from datetime import datetime
    threat.detected_by = "analyst_assessed"
    threat.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(threat)
    return threat


@router.delete("/{threat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_threat(
    threat_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Delete a threat.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        success = ThreatService.delete_threat(
            db=db,
            threat_id=threat_id,
            tenant_id=tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Threat {threat_id} not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats/count", response_model=dict)
def get_threat_stats(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get threat statistics (count).
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    count = ThreatService.get_threat_count(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        severity=severity
    )
    
    return {
        "count": count,
        "assessment_id": assessment_id,
        "severity_filter": severity
    }
