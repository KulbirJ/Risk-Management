"""Audit Log service layer for immutable change tracking."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..models.models import AuditLog


class AuditLogService:
    """Service for audit log management."""

    @staticmethod
    def create_audit_log(
        db: Session,
        tenant_id: UUID,
        actor_user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> AuditLog:
        """
        Create an immutable audit log entry.
        
        This should be called automatically for all CREATE, UPDATE, DELETE operations.
        """
        audit_log = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action_type=action,
            resource_type=entity_type,
            resource_id=str(entity_id),
            changes={
                "before": old_value or {},
                "after": new_value or {},
                "metadata": metadata or {}
            }
        )
        
        try:
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            return audit_log
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error creating audit log: {str(e)}")

    @staticmethod
    def get_audit_log(
        db: Session,
        log_id: UUID,
        tenant_id: UUID
    ) -> Optional[AuditLog]:
        """Get a single audit log entry by ID."""
        return db.query(AuditLog).filter(
            AuditLog.id == log_id,
            AuditLog.tenant_id == tenant_id
        ).first()

    @staticmethod
    def list_audit_logs(
        db: Session,
        tenant_id: UUID,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        actor_user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """List audit logs with optional filters."""
        query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)
        
        if entity_type:
            query = query.filter(AuditLog.resource_type == entity_type)
        
        if entity_id:
            query = query.filter(AuditLog.resource_id == str(entity_id))
        
        if actor_user_id:
            query = query.filter(AuditLog.actor_user_id == actor_user_id)
        
        if action:
            query = query.filter(AuditLog.action_type == action)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_entity_history(
        db: Session,
        entity_id: UUID,
        entity_type: str,
        tenant_id: UUID,
        limit: int = 50
    ) -> List[AuditLog]:
        """Get complete change history for a specific entity."""
        return db.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.resource_type == entity_type,
            AuditLog.resource_id == str(entity_id)
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_audit_count(
        db: Session,
        tenant_id: UUID,
        entity_type: Optional[str] = None,
        action: Optional[str] = None
    ) -> int:
        """Get count of audit logs."""
        query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)
        
        if entity_type:
            query = query.filter(AuditLog.resource_type == entity_type)
        
        if action:
            query = query.filter(AuditLog.action_type == action)
        
        return query.count()
