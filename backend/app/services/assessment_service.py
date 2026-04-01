"""Assessment service layer for business logic and database operations."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..models.models import Assessment, User
from ..schemas.schemas import AssessmentCreate, AssessmentUpdate


class AssessmentService:
    """Service for managing risk assessments."""

    @staticmethod
    def create_assessment(
        db: Session,
        assessment_data: AssessmentCreate,
        tenant_id: UUID,
        user_id: UUID
    ) -> Assessment:
        """Create a new assessment."""
        # Verify user exists and belongs to tenant
        user = db.query(User).filter(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise ValueError("User not found or not active in this tenant")

        assessment = Assessment(
            tenant_id=tenant_id,
            owner_user_id=user_id,
            title=assessment_data.title,
            description=assessment_data.description,
            system_background=assessment_data.system_background,
            scope=assessment_data.scope,
            tech_stack=assessment_data.tech_stack or [],
            industry_sector=assessment_data.industry_sector,
            overall_impact=assessment_data.overall_impact,
            status="draft"
        )
        
        try:
            db.add(assessment)
            db.commit()
            db.refresh(assessment)
            return assessment
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error creating assessment: {str(e)}")

    @staticmethod
    def get_assessment(
        db: Session,
        assessment_id: UUID,
        tenant_id: UUID
    ) -> Optional[Assessment]:
        """Get a single assessment by ID."""
        return db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()

    @staticmethod
    def list_assessments(
        db: Session,
        tenant_id: UUID,
        status: Optional[str] = None,
        owner_user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assessment]:
        """List assessments with optional filters."""
        query = db.query(Assessment).filter(Assessment.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Assessment.status == status)
        else:
            # By default, exclude archived assessments
            query = query.filter(Assessment.status != "archived")
        
        if owner_user_id:
            query = query.filter(Assessment.owner_user_id == owner_user_id)
        
        return query.order_by(Assessment.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_assessment(
        db: Session,
        assessment_id: UUID,
        tenant_id: UUID,
        update_data: AssessmentUpdate
    ) -> Optional[Assessment]:
        """Update an existing assessment."""
        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()
        
        if not assessment:
            return None

        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(assessment, field, value)
        
        assessment.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(assessment)
            return assessment
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error updating assessment: {str(e)}")

    @staticmethod
    def delete_assessment(
        db: Session,
        assessment_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete an assessment (soft delete by archiving)."""
        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()
        
        if not assessment:
            return False

        # Soft delete by archiving
        assessment.status = "archived"
        assessment.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error deleting assessment: {str(e)}")

    @staticmethod
    def get_assessment_count(
        db: Session,
        tenant_id: UUID,
        status: Optional[str] = None
    ) -> int:
        """Get count of assessments."""
        query = db.query(Assessment).filter(Assessment.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Assessment.status == status)
        
        return query.count()
