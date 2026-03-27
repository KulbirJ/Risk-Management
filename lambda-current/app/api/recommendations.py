"""Recommendation API router endpoints."""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import RecommendationCreate, RecommendationRead, RecommendationUpdate
from ..services.recommendation_service import RecommendationService

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


@router.post("/", response_model=RecommendationRead, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    recommendation: RecommendationCreate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Create a new recommendation.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        created_recommendation = RecommendationService.create_recommendation(
            db=db,
            recommendation_data=recommendation,
            tenant_id=tenant_id
        )
        return created_recommendation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{recommendation_id}", response_model=RecommendationRead)
def get_recommendation(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get a specific recommendation by ID.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    recommendation = RecommendationService.get_recommendation(
        db=db,
        recommendation_id=recommendation_id,
        tenant_id=tenant_id
    )
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found"
        )
    
    return recommendation


@router.get("/", response_model=List[RecommendationRead])
def list_recommendations(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    threat_id: Optional[UUID] = Query(None, description="Filter by threat ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (open, in_progress, done, accepted)"),
    priority: Optional[str] = Query(None, description="Filter by priority (Low, Medium, High)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of records to return"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    List all recommendations for the tenant with optional filters.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    recommendations = RecommendationService.list_recommendations(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        threat_id=threat_id,
        status=status_filter,
        priority=priority,
        skip=skip,
        limit=limit
    )
    
    return recommendations


@router.patch("/{recommendation_id}", response_model=RecommendationRead)
def update_recommendation(
    recommendation_id: UUID,
    update_data: RecommendationUpdate,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Update an existing recommendation.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        updated_recommendation = RecommendationService.update_recommendation(
            db=db,
            recommendation_id=recommendation_id,
            tenant_id=tenant_id,
            update_data=update_data
        )
        
        if not updated_recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {recommendation_id} not found"
            )
        
        return updated_recommendation
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{recommendation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recommendation(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Delete a recommendation.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        success = RecommendationService.delete_recommendation(
            db=db,
            recommendation_id=recommendation_id,
            tenant_id=tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {recommendation_id} not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats/count", response_model=dict)
def get_recommendation_stats(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get recommendation statistics (count).
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    count = RecommendationService.get_recommendation_count(
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
