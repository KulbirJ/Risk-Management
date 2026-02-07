"""Active Risk API router endpoints."""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import ActiveRiskCreate, ActiveRiskRead, ActiveRiskUpdate
from ..services.active_risk_service import ActiveRiskService

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


@router.post("/", response_model=ActiveRiskRead, status_code=status.HTTP_201_CREATED)
def create_active_risk(
    risk: ActiveRiskCreate,
    assessment_id: UUID = Query(..., description="Assessment ID to link active risk to"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Create a new active risk entry for the risk register.
    
    Active risks are threats that cannot be fully remediated and must be
    accepted and monitored by a risk owner.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    
    Query parameters:
    - assessment_id: UUID of the assessment this active risk belongs to
    """
    tenant_id, _ = context
    
    try:
        created_risk = ActiveRiskService.create_active_risk(
            db=db,
            risk_data=risk,
            assessment_id=assessment_id,
            tenant_id=tenant_id
        )
        return created_risk
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{risk_id}", response_model=ActiveRiskRead)
def get_active_risk(
    risk_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get a specific active risk by ID.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    risk = ActiveRiskService.get_active_risk(
        db=db,
        risk_id=risk_id,
        tenant_id=tenant_id
    )
    
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active risk {risk_id} not found"
        )
    
    return risk


@router.get("/", response_model=List[ActiveRiskRead])
def list_active_risks(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (open, accepted, mitigating, closed)"),
    risk_owner_id: Optional[UUID] = Query(None, description="Filter by risk owner ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of records to return"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    List all active risks for the tenant with optional filters.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    risks = ActiveRiskService.list_active_risks(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        status=status_filter,
        risk_owner_id=risk_owner_id,
        skip=skip,
        limit=limit
    )
    
    return risks


@router.patch("/{risk_id}", response_model=ActiveRiskRead)
def update_active_risk(
    risk_id: UUID,
    update_data: ActiveRiskUpdate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Update an existing active risk.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        updated_risk = ActiveRiskService.update_active_risk(
            db=db,
            risk_id=risk_id,
            tenant_id=tenant_id,
            update_data=update_data
        )
        
        if not updated_risk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active risk {risk_id} not found"
            )
        
        return updated_risk
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{risk_id}/accept", response_model=ActiveRiskRead)
def accept_risk(
    risk_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Accept an active risk (convenience endpoint).
    
    This sets the status to 'accepted' and records the acceptance date.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        accepted_risk = ActiveRiskService.accept_risk(
            db=db,
            risk_id=risk_id,
            tenant_id=tenant_id
        )
        
        if not accepted_risk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active risk {risk_id} not found"
            )
        
        return accepted_risk
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_active_risk(
    risk_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Delete an active risk.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        success = ActiveRiskService.delete_active_risk(
            db=db,
            risk_id=risk_id,
            tenant_id=tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active risk {risk_id} not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats/count", response_model=dict)
def get_active_risk_stats(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get active risk statistics (count).
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    count = ActiveRiskService.get_active_risk_count(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        status=status_filter
    )
    
    return {
        "count": count,
        "assessment_id": assessment_id,
        "status_filter": status_filter
    }
