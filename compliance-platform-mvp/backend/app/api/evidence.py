"""Evidence API router endpoints."""
from uuid import UUID, uuid4
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import EvidenceInitRequest, EvidenceRead
from ..services.evidence_service import EvidenceService

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


@router.post("/", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(
    evidence: EvidenceInitRequest,
    assessment_id: UUID = Query(..., description="Assessment ID to link evidence to"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Create a new evidence record.
    
    Note: For Phase 0 MVP, this creates a record with a mock S3 key.
    In production, this would integrate with S3 presigned URLs for direct upload.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    
    Query parameters:
    - assessment_id: UUID of the assessment this evidence belongs to
    """
    tenant_id, user_id = context
    
    # Mock S3 key for Phase 0 (in production, this would be from actual S3 upload)
    s3_key = f"evidence/{tenant_id}/{assessment_id}/{uuid4()}/{evidence.file_name}"
    
    try:
        created_evidence = EvidenceService.create_evidence(
            db=db,
            evidence_data=evidence,
            assessment_id=assessment_id,
            tenant_id=tenant_id,
            user_id=user_id,
            s3_key=s3_key
        )
        return created_evidence
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{evidence_id}", response_model=EvidenceRead)
def get_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get a specific evidence record by ID.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    evidence = EvidenceService.get_evidence(
        db=db,
        evidence_id=evidence_id,
        tenant_id=tenant_id
    )
    
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found"
        )
    
    return evidence


@router.get("/", response_model=List[EvidenceRead])
def list_evidence(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    threat_id: Optional[UUID] = Query(None, description="Filter by threat ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of records to return"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    List all evidence for the tenant with optional filters.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    evidence_list = EvidenceService.list_evidence(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id,
        threat_id=threat_id,
        skip=skip,
        limit=limit
    )
    
    return evidence_list


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Delete an evidence record.
    
    Note: In production, this should also delete the file from S3.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    try:
        success = EvidenceService.delete_evidence(
            db=db,
            evidence_id=evidence_id,
            tenant_id=tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence {evidence_id} not found"
            )
        
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/stats/count", response_model=dict)
def get_evidence_stats(
    assessment_id: Optional[UUID] = Query(None, description="Filter by assessment ID"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get evidence statistics (count).
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    count = EvidenceService.get_evidence_count(
        db=db,
        tenant_id=tenant_id,
        assessment_id=assessment_id
    )
    
    return {"count": count, "assessment_id": assessment_id}
