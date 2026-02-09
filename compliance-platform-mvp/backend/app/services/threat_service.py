"""Threat service layer for business logic and database operations."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..models.models import Threat, Assessment
from ..schemas.schemas import ThreatCreate, ThreatPatch


class ThreatService:
    """Service for managing identified threats."""

    @staticmethod
    def _calculate_severity(likelihood: str, impact: str) -> str:
        """Calculate threat severity based on likelihood and impact."""
        severity_matrix = {
            ("Low", "Low"): "Low",
            ("Low", "Medium"): "Low",
            ("Low", "High"): "Medium",
            ("Low", "Critical"): "Medium",
            ("Medium", "Low"): "Low",
            ("Medium", "Medium"): "Medium",
            ("Medium", "High"): "High",
            ("Medium", "Critical"): "High",
            ("High", "Low"): "Medium",
            ("High", "Medium"): "High",
            ("High", "High"): "Critical",
            ("High", "Critical"): "Critical",
            ("Critical", "Low"): "Medium",
            ("Critical", "Medium"): "High",
            ("Critical", "High"): "Critical",
            ("Critical", "Critical"): "Critical",
        }
        return severity_matrix.get((likelihood, impact), "Medium")

    @staticmethod
    def create_threat(
        db: Session,
        threat_data: ThreatCreate,
        assessment_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Threat:
        """Create a new threat for an assessment."""
        # Verify assessment exists and belongs to tenant
        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()
        
        if not assessment:
            raise ValueError("Assessment not found in this tenant")

        # Calculate severity
        severity = ThreatService._calculate_severity(
            threat_data.likelihood,
            threat_data.impact
        )

        threat = Threat(
            tenant_id=tenant_id,
            assessment_id=assessment_id,
            created_by_id=user_id,
            catalogue_key=threat_data.catalogue_key,
            title=threat_data.title,
            description=threat_data.description,
            recommendation=threat_data.recommendation,
            detected_by=threat_data.detected_by,
            cve_ids=threat_data.cve_ids or [],
            cvss_score=threat_data.cvss_score,
            likelihood=threat_data.likelihood,
            impact=threat_data.impact,
            severity=severity
        )
        
        try:
            db.add(threat)
            db.commit()
            db.refresh(threat)
            return threat
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error creating threat: {str(e)}")

    @staticmethod
    def get_threat(
        db: Session,
        threat_id: UUID,
        tenant_id: UUID
    ) -> Optional[Threat]:
        """Get a single threat by ID."""
        return db.query(Threat).filter(
            Threat.id == threat_id,
            Threat.tenant_id == tenant_id
        ).first()

    @staticmethod
    def list_threats(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Threat]:
        """List threats with optional filters."""
        query = db.query(Threat).filter(Threat.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(Threat.assessment_id == assessment_id)
        
        if severity:
            query = query.filter(Threat.severity == severity)
        
        return query.order_by(Threat.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_threat(
        db: Session,
        threat_id: UUID,
        tenant_id: UUID,
        update_data: ThreatPatch
    ) -> Optional[Threat]:
        """Update an existing threat."""
        threat = db.query(Threat).filter(
            Threat.id == threat_id,
            Threat.tenant_id == tenant_id
        ).first()
        
        if not threat:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(threat, field, value)
        
        # Recalculate severity if likelihood or impact changed
        if 'likelihood' in update_dict or 'impact' in update_dict:
            threat.severity = ThreatService._calculate_severity(
                threat.likelihood,
                threat.impact
            )
        
        threat.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(threat)
            return threat
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error updating threat: {str(e)}")

    @staticmethod
    def delete_threat(
        db: Session,
        threat_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete a threat."""
        threat = db.query(Threat).filter(
            Threat.id == threat_id,
            Threat.tenant_id == tenant_id
        ).first()
        
        if not threat:
            return False

        try:
            db.delete(threat)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error deleting threat: {str(e)}")

    @staticmethod
    def get_threat_count(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None,
        severity: Optional[str] = None
    ) -> int:
        """Get count of threats."""
        query = db.query(Threat).filter(Threat.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(Threat.assessment_id == assessment_id)
        
        if severity:
            query = query.filter(Threat.severity == severity)
        
        return query.count()
