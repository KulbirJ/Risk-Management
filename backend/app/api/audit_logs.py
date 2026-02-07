"""Audit Log API router endpoints."""
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import AuditLogRead
from ..services.audit_log_service import AuditLogService

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


@router.get("/{log_id}", response_model=AuditLogRead)
def get_audit_log(
    log_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get a specific audit log entry by ID.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    log = AuditLogService.get_audit_log(
        db=db,
        log_id=log_id,
        tenant_id=tenant_id
    )
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log {log_id} not found"
        )
    
    return log


@router.get("/", response_model=List[AuditLogRead])
def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (assessment, threat, evidence, etc.)"),
    entity_id: Optional[UUID] = Query(None, description="Filter by entity ID"),
    actor_user_id: Optional[UUID] = Query(None, description="Filter by user who performed the action"),
    action: Optional[str] = Query(None, description="Filter by action (CREATE, UPDATE, DELETE)"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of records to return"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    List audit logs for the tenant with optional filters.
    
    Audit logs are immutable records of all CREATE, UPDATE, and DELETE operations.
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    logs = AuditLogService.list_audit_logs(
        db=db,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    
    return logs


@router.get("/entity/{entity_id}", response_model=List[AuditLogRead])
def get_entity_history(
    entity_id: UUID,
    entity_type: str = Query(..., description="Entity type (assessment, threat, evidence, etc.)"),
    limit: int = Query(50, ge=1, le=500, description="Max number of records to return"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get complete change history for a specific entity.
    
    Returns all audit log entries for the specified entity, ordered by timestamp (newest first).
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    history = AuditLogService.get_entity_history(
        db=db,
        entity_id=entity_id,
        entity_type=entity_type,
        tenant_id=tenant_id,
        limit=limit
    )
    
    return history


@router.get("/stats/count", response_model=dict)
def get_audit_stats(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get audit log statistics (count).
    
    Requires headers:
    - X-Tenant-Id: Tenant UUID
    - X-User-Id: User UUID
    """
    tenant_id, _ = context
    
    count = AuditLogService.get_audit_count(
        db=db,
        tenant_id=tenant_id,
        entity_type=entity_type,
        action=action
    )
    
    return {
        "count": count,
        "entity_type": entity_type,
        "action_filter": action
    }
