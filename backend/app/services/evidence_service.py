"""Evidence service layer for business logic and database operations."""
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

from ..models.models import Evidence, Assessment, Threat
from ..schemas.schemas import EvidenceInitRequest

logger = logging.getLogger(__name__)


class EvidenceService:
    """Service for managing evidence files."""

    @staticmethod
    def create_evidence(
        db: Session,
        evidence_data: EvidenceInitRequest,
        assessment_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        s3_key: str,
        initial_status: str = "processing"
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
            status=initial_status,
            document_type=getattr(evidence_data, 'document_type', None) or 'other'
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
    def process_uploaded_document(
        db: Session,
        evidence_id: UUID,
        tenant_id: UUID
    ) -> Evidence:
        """
        Process an uploaded document: download from S3, extract text, update record.
        Called after the client confirms upload is complete.
        """
        from ..services.document_parser import DocumentParser
        from ..utils.s3 import get_s3_object_content

        evidence = db.query(Evidence).filter(
            Evidence.id == evidence_id,
            Evidence.tenant_id == tenant_id
        ).first()

        if not evidence:
            raise ValueError("Evidence not found")

        try:
            # Download file content from S3
            file_bytes = get_s3_object_content(evidence.s3_key)

            # Parse document and extract text
            result = DocumentParser.parse(
                file_bytes=file_bytes,
                file_name=evidence.file_name,
                mime_type=evidence.mime_type
            )

            # Strip NUL bytes — PostgreSQL TEXT columns reject \x00
            raw_text = result.get("text", "")
            evidence.extracted_text = raw_text.replace("\x00", "") if raw_text else ""
            evidence.extract_metadata = result.get("metadata", {})
            evidence.status = "ready"

            # Auto-detect document type if not set
            if not evidence.document_type or evidence.document_type == "other":
                doc_type, confidence = DocumentParser.detect_document_type_with_confidence(
                    text=evidence.extracted_text,
                    file_name=evidence.file_name
                )
                evidence.document_type = doc_type
                if hasattr(evidence, 'document_type_confidence'):
                    evidence.document_type_confidence = confidence

            # Extract structured metadata based on document type
            structured_meta = DocumentParser.extract_structured_metadata(
                text=evidence.extracted_text,
                document_type=evidence.document_type,
                file_name=evidence.file_name,
            )
            if structured_meta:
                existing_meta = evidence.extract_metadata or {}
                existing_meta["structured"] = structured_meta
                evidence.extract_metadata = existing_meta

            db.commit()
            db.refresh(evidence)
            logger.info(f"Successfully processed evidence {evidence_id}: {len(evidence.extracted_text or '')} chars extracted")
            return evidence

        except Exception as e:
            logger.error(f"Error processing document {evidence_id}: {e}")
            evidence.status = "failed"
            evidence.extract_metadata = {"error": str(e)}
            db.commit()
            db.refresh(evidence)
            return evidence

    @staticmethod
    def update_evidence_status(
        db: Session,
        evidence_id: UUID,
        tenant_id: UUID,
        status: str
    ) -> Optional[Evidence]:
        """Update the status of an evidence record."""
        evidence = db.query(Evidence).filter(
            Evidence.id == evidence_id,
            Evidence.tenant_id == tenant_id
        ).first()
        if evidence:
            evidence.status = status
            db.commit()
            db.refresh(evidence)
        return evidence

    @staticmethod
    def get_evidence_for_assessment(
        db: Session,
        assessment_id: UUID,
        tenant_id: UUID,
        status_filter: str = "ready"
    ) -> List[Evidence]:
        """Get all ready evidence with extracted text for an assessment (used by AI enrichment)."""
        query = db.query(Evidence).filter(
            Evidence.assessment_id == assessment_id,
            Evidence.tenant_id == tenant_id,
            Evidence.status == status_filter
        )
        return query.order_by(Evidence.created_at.desc()).all()

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
