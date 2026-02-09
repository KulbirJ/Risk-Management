"""Assessment API router endpoints."""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import AssessmentCreate, AssessmentRead, AssessmentUpdate
from ..services.assessment_service import AssessmentService

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
