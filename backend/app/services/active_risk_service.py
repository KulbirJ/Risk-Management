"""Active Risk service layer for risk register management."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..models.models import ActiveRisk, Assessment, Threat, User
from ..schemas.schemas import ActiveRiskCreate, ActiveRiskUpdate


class ActiveRiskService:
    """Service for managing active risk register."""

    @staticmethod
    def create_active_risk(
        db: Session,
        risk_data: ActiveRiskCreate,
        assessment_id: UUID,
        tenant_id: UUID
    ) -> ActiveRisk:
        """Create a new active risk entry."""
        # Verify assessment exists
        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()
        
        if not assessment:
            raise ValueError("Assessment not found in this tenant")

        # Verify threat exists and belongs to this assessment
        threat = db.query(Threat).filter(
            Threat.id == risk_data.threat_id,
            Threat.assessment_id == assessment_id,
            Threat.tenant_id == tenant_id
        ).first()
        
        if not threat:
            raise ValueError("Threat not found in this assessment")

        # Verify risk owner exists
        risk_owner = db.query(User).filter(
            User.id == risk_data.risk_owner_id,
            User.tenant_id == tenant_id,
            User.is_active == True
        ).first()
        
        if not risk_owner:
            raise ValueError("Risk owner not found or inactive")

        # Check if active risk already exists for this threat
        existing = db.query(ActiveRisk).filter(
            ActiveRisk.threat_id == risk_data.threat_id,
            ActiveRisk.tenant_id == tenant_id
        ).first()
        
        if existing:
            raise ValueError("Active risk already exists for this threat")

        active_risk = ActiveRisk(
            tenant_id=tenant_id,
            assessment_id=assessment_id,
            threat_id=risk_data.threat_id,
            title=risk_data.title,
            residual_risk=risk_data.residual_risk,
            risk_owner_id=risk_data.risk_owner_id,
            mitigation_plan=risk_data.mitigation_plan,
            review_cycle_days=risk_data.review_cycle_days,
            status="open"
        )
        
        try:
            db.add(active_risk)
            db.commit()
            db.refresh(active_risk)
            return active_risk
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error creating active risk: {str(e)}")

    @staticmethod
    def get_active_risk(
        db: Session,
        risk_id: UUID,
        tenant_id: UUID
    ) -> Optional[ActiveRisk]:
        """Get a single active risk by ID."""
        return db.query(ActiveRisk).filter(
            ActiveRisk.id == risk_id,
            ActiveRisk.tenant_id == tenant_id
        ).first()

    @staticmethod
    def list_active_risks(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None,
        status: Optional[str] = None,
        risk_owner_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ActiveRisk]:
        """List active risks with optional filters."""
        query = db.query(ActiveRisk).filter(ActiveRisk.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(ActiveRisk.assessment_id == assessment_id)
        
        if status:
            query = query.filter(ActiveRisk.status == status)
        
        if risk_owner_id:
            query = query.filter(ActiveRisk.risk_owner_id == risk_owner_id)
        
        return query.order_by(ActiveRisk.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_active_risk(
        db: Session,
        risk_id: UUID,
        tenant_id: UUID,
        update_data: ActiveRiskUpdate
    ) -> Optional[ActiveRisk]:
        """Update an existing active risk."""
        active_risk = db.query(ActiveRisk).filter(
            ActiveRisk.id == risk_id,
            ActiveRisk.tenant_id == tenant_id
        ).first()
        
        if not active_risk:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(active_risk, field, value)
        
        # Set acceptance date when status changes to 'accepted'
        if 'status' in update_dict and update_dict['status'] == 'accepted':
            if not active_risk.acceptance_date:
                active_risk.acceptance_date = datetime.utcnow()
        
        active_risk.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(active_risk)
            return active_risk
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error updating active risk: {str(e)}")

    @staticmethod
    def delete_active_risk(
        db: Session,
        risk_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete an active risk."""
        active_risk = db.query(ActiveRisk).filter(
            ActiveRisk.id == risk_id,
            ActiveRisk.tenant_id == tenant_id
        ).first()
        
        if not active_risk:
            return False

        try:
            db.delete(active_risk)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error deleting active risk: {str(e)}")

    @staticmethod
    def accept_risk(
        db: Session,
        risk_id: UUID,
        tenant_id: UUID
    ) -> Optional[ActiveRisk]:
        """Accept an active risk (convenience method)."""
        update_data = ActiveRiskUpdate(status="accepted")
        return ActiveRiskService.update_active_risk(db, risk_id, tenant_id, update_data)

    @staticmethod
    def get_active_risk_count(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> int:
        """Get count of active risks."""
        query = db.query(ActiveRisk).filter(ActiveRisk.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(ActiveRisk.assessment_id == assessment_id)
        
        if status:
            query = query.filter(ActiveRisk.status == status)
        
        return query.count()
