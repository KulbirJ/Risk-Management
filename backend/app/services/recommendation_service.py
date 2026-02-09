"""Recommendation service layer for business logic and database operations."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..models.models import Recommendation, Assessment, Threat
from ..schemas.schemas import RecommendationCreate, RecommendationUpdate


class RecommendationService:
    """Service for managing recommendations."""

    @staticmethod
    def create_recommendation(
        db: Session,
        recommendation_data: RecommendationCreate,
        tenant_id: UUID
    ) -> Recommendation:
        """Create a new recommendation."""
        # Verify assessment exists
        assessment = db.query(Assessment).filter(
            Assessment.id == recommendation_data.assessment_id,
            Assessment.tenant_id == tenant_id
        ).first()
        
        if not assessment:
            raise ValueError("Assessment not found in this tenant")

        # If threat_id provided, verify it belongs to this assessment
        if recommendation_data.threat_id:
            threat = db.query(Threat).filter(
                Threat.id == recommendation_data.threat_id,
                Threat.assessment_id == recommendation_data.assessment_id,
                Threat.tenant_id == tenant_id
            ).first()
            
            if not threat:
                raise ValueError("Threat not found in this assessment")

        recommendation = Recommendation(
            tenant_id=tenant_id,
            assessment_id=recommendation_data.assessment_id,
            threat_id=recommendation_data.threat_id,
            text=recommendation_data.text,
            type=recommendation_data.type,
            priority=recommendation_data.priority,
            owner_user_id=recommendation_data.owner_user_id,
            target_date=recommendation_data.target_date,
            status="open"
        )
        
        try:
            db.add(recommendation)
            db.commit()
            db.refresh(recommendation)
            return recommendation
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error creating recommendation: {str(e)}")

    @staticmethod
    def get_recommendation(
        db: Session,
        recommendation_id: UUID,
        tenant_id: UUID
    ) -> Optional[Recommendation]:
        """Get a single recommendation by ID."""
        return db.query(Recommendation).filter(
            Recommendation.id == recommendation_id,
            Recommendation.tenant_id == tenant_id
        ).first()

    @staticmethod
    def list_recommendations(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None,
        threat_id: Optional[UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Recommendation]:
        """List recommendations with optional filters."""
        query = db.query(Recommendation).filter(Recommendation.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(Recommendation.assessment_id == assessment_id)
        
        if threat_id:
            query = query.filter(Recommendation.threat_id == threat_id)
        
        if status:
            query = query.filter(Recommendation.status == status)
        
        if priority:
            query = query.filter(Recommendation.priority == priority)
        
        return query.order_by(Recommendation.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_recommendation(
        db: Session,
        recommendation_id: UUID,
        tenant_id: UUID,
        update_data: RecommendationUpdate
    ) -> Optional[Recommendation]:
        """Update an existing recommendation."""
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == recommendation_id,
            Recommendation.tenant_id == tenant_id
        ).first()
        
        if not recommendation:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(recommendation, field, value)
        
        recommendation.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(recommendation)
            return recommendation
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error updating recommendation: {str(e)}")

    @staticmethod
    def delete_recommendation(
        db: Session,
        recommendation_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete a recommendation."""
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == recommendation_id,
            Recommendation.tenant_id == tenant_id
        ).first()
        
        if not recommendation:
            return False

        try:
            db.delete(recommendation)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            raise Exception(f"Database error deleting recommendation: {str(e)}")

    @staticmethod
    def get_recommendation_count(
        db: Session,
        tenant_id: UUID,
        assessment_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> int:
        """Get count of recommendations."""
        query = db.query(Recommendation).filter(Recommendation.tenant_id == tenant_id)
        
        if assessment_id:
            query = query.filter(Recommendation.assessment_id == assessment_id)
        
        if status:
            query = query.filter(Recommendation.status == status)
        
        return query.count()
