"""Evidence service layer for business logic and database operations."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..models.models import Evidence, Assessment, Threat
from ..schemas.schemas import EvidenceInitRequest


class EvidenceService:
    """Service for managing evidence files."""

    @staticmethod
    def create_evidence(
        db: Session,
        evidence_data: EvidenceInitRequest,
        assessment_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        s3_key: str
    ) -> Evidence:
        """Create a new evidence record."""
        # Verify assessment exists
        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()
        
        if not assessment:
            raise ValueError("Assessment not found in this tenant")

        # If threat_id provided, verify it belongs to this assessment
        if evidence_data.threat_id:
            threat = db.query(Threat).filter(
                Threat.id == evidence_data.threat_id,
                Threat.assessment_id == assessment_id,
                Threat.tenant_id == tenant_id
            ).first()
            
            if not threat:
                raise ValueError("Threat not found in this assessment")

        evidence = Evidence(
            tenant_id=tenant_id,
            assessment_id=assessment_id,
            threat_id=evidence_data.threat_id,
            uploaded_by_id=user_id,
            s3_key=s3_key,
            file_name=evidence_data.file_name,
            mime_type=evidence_data.content_type,
            size_bytes=evidence_data.size_bytes,
            status="ready"
        )
        
        try:
            db.add(evidence)
            db.commit()
            db.refresh(evidence)
            return evidence
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error creating evidence: {str(e)}")

    @staticmethod
    def get_evidence(
        db: Session,
        evidence_id: UUID,
        tenant_id: UUID
    ) -> Optional[Evidence]:
        """Get a single evidence record by ID."""
        return db.query(Evidence).filter(
            Evidence.id == evidence_id,
            Evidence.tenant_id == tenant_id
        ).first()

    @staticmethod
    def list_evidence(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None,
        threat_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Evidence]:
        """List evidence with optional filters."""
        query = db.query(Evidence).filter(Evidence.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(Evidence.assessment_id == assessment_id)
        
        if threat_id:
            query = query.filter(Evidence.threat_id == threat_id)
        
        return query.order_by(Evidence.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def delete_evidence(
        db: Session,
        evidence_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete an evidence record."""
        evidence = db.query(Evidence).filter(
            Evidence.id == evidence_id,
            Evidence.tenant_id == tenant_id
        ).first()
        
        if not evidence:
            return False

        try:
            db.delete(evidence)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error deleting evidence: {str(e)}")

    @staticmethod
    def get_evidence_count(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None
    ) -> int:
        """Get count of evidence records."""
        query = db.query(Evidence).filter(Evidence.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(Evidence.assessment_id == assessment_id)
        
        return query.count()
