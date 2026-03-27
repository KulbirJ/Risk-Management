"""Evidence API router endpoints."""
from uuid import UUID, uuid4
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, UploadFile, File as FastAPIFile, Form, status
from sqlalchemy.orm import Session
import logging

from ..db.database import get_db
from ..schemas.schemas import EvidenceInitRequest, EvidenceInitResponse, EvidenceRead
from ..services.evidence_service import EvidenceService
from ..utils.s3 import (
    generate_evidence_s3_key,
    generate_presigned_upload_url,
    generate_presigned_download_url,
    verify_s3_upload,
    delete_evidence_from_s3,
    get_s3_client,
)
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


@router.post("/initiate", response_model=EvidenceInitResponse, status_code=status.HTTP_201_CREATED)
def initiate_upload(
    evidence: EvidenceInitRequest,
    assessment_id: UUID = Query(..., description="Assessment ID to link evidence to"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Initiate a file upload: creates an evidence record and returns a presigned S3 URL.
    The client should upload the file directly to S3 using the returned URL and fields,
    then call POST /evidence/{id}/complete to finalize.
    """
    tenant_id, user_id = context

    # Generate S3 key
    s3_key = generate_evidence_s3_key(tenant_id, assessment_id, evidence.file_name)

    try:
        # Generate presigned upload URL
        upload_url, upload_fields = generate_presigned_upload_url(
            s3_key=s3_key,
            content_type=evidence.content_type
        )

        # Create evidence record in "processing" state
        created_evidence = EvidenceService.create_evidence(
            db=db,
            evidence_data=evidence,
            assessment_id=assessment_id,
            tenant_id=tenant_id,
            user_id=user_id,
            s3_key=s3_key,
            initial_status="processing"
        )

        return EvidenceInitResponse(
            evidence_id=created_evidence.id,
            upload_url=upload_url,
            upload_fields=upload_fields,
            s3_key=s3_key,
            upload_method="POST",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error initiating upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{evidence_id}/complete", response_model=EvidenceRead)
def complete_upload(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Complete a file upload after the client has uploaded to S3.
    Verifies the file exists in S3, triggers document parsing, and marks as ready.
    """
    tenant_id, user_id = context

    evidence = EvidenceService.get_evidence(db=db, evidence_id=evidence_id, tenant_id=tenant_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    # Verify file exists in S3
    if not verify_s3_upload(evidence.s3_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found in S3. Upload may not have completed."
        )

    try:
        # Parse the document and extract text
        updated_evidence = EvidenceService.process_uploaded_document(
            db=db,
            evidence_id=evidence_id,
            tenant_id=tenant_id
        )
        return updated_evidence
    except Exception as e:
        logger.error(f"Error completing upload for {evidence_id}: {e}")
        # Mark as failed if processing errors, but still return the record (not 500)
        try:
            EvidenceService.update_evidence_status(db, evidence_id, tenant_id, "failed")
            evidence = EvidenceService.get_evidence(db=db, evidence_id=evidence_id, tenant_id=tenant_id)
            if evidence:
                return evidence
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/proxy-upload")
async def proxy_upload(
    file: UploadFile = FastAPIFile(...),
    s3_key: str = Form(...),
    content_type: str = Form("application/octet-stream"),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Proxy upload: client sends file to backend, backend uploads to S3.
    Used as fallback when direct S3 upload fails due to CORS or network issues.
    Limited by API Gateway / Lambda payload limits (~6MB).
    """
    try:
        file_bytes = await file.read()
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.s3_bucket_evidence,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        return {"status": "uploaded", "s3_key": s3_key, "size": len(file_bytes)}
    except Exception as e:
        logger.error(f"Proxy upload failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{evidence_id}/retry", response_model=EvidenceRead)
def retry_processing(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Retry processing for stuck evidence (status=processing or failed).
    Re-verifies S3 upload and re-triggers document parsing.
    """
    tenant_id, user_id = context

    evidence = EvidenceService.get_evidence(db=db, evidence_id=evidence_id, tenant_id=tenant_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    if evidence.status == "ready":
        return evidence  # Already processed

    # Check if file is actually in S3
    if not verify_s3_upload(evidence.s3_key):
        # File never made it to S3 - mark as failed
        EvidenceService.update_evidence_status(db, evidence_id, tenant_id, "failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found in S3. Please delete this entry and re-upload."
        )

    try:
        updated_evidence = EvidenceService.process_uploaded_document(
            db=db,
            evidence_id=evidence_id,
            tenant_id=tenant_id
        )
        return updated_evidence
    except Exception as e:
        logger.error(f"Error retrying processing for {evidence_id}: {e}")
        EvidenceService.update_evidence_status(db, evidence_id, tenant_id, "failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(
    evidence: EvidenceInitRequest,
    assessment_id: UUID = Query(..., description="Assessment ID to link evidence to"),
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Create a new evidence record (legacy endpoint for backward compatibility).
    Use POST /initiate for the full presigned upload flow.
    """
    tenant_id, user_id = context
    s3_key = f"evidence/{tenant_id}/{assessment_id}/{uuid4()}/{evidence.file_name}"

    try:
        created_evidence = EvidenceService.create_evidence(
            db=db,
            evidence_data=evidence,
            assessment_id=assessment_id,
            tenant_id=tenant_id,
            user_id=user_id,
            s3_key=s3_key,
            initial_status="ready"
        )
        return created_evidence
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/download/{evidence_id}")
def get_download_url(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """Get a presigned download URL for an evidence file."""
    tenant_id, _ = context
    
    evidence = EvidenceService.get_evidence(db=db, evidence_id=evidence_id, tenant_id=tenant_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    try:
        url = generate_presigned_download_url(evidence.s3_key)
        return {"download_url": url, "file_name": evidence.file_name}
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


@router.get("/{evidence_id}/analysis")
def get_evidence_analysis(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Get the stored analysis results for a single evidence file.
    Returns analysis_summary, analysis_findings, risk_indicators, extract_metadata,
    and document_type. If the file has not been analyzed yet, returns extracted_text
    preview with enrichment_pending=True.
    """
    tenant_id, _ = context

    evidence = EvidenceService.get_evidence(db=db, evidence_id=evidence_id, tenant_id=tenant_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    has_analysis = bool(getattr(evidence, 'analysis_summary', None))

    return {
        "evidence_id": str(evidence.id),
        "file_name": evidence.file_name,
        "document_type": evidence.document_type,
        "document_type_confidence": getattr(evidence, 'document_type_confidence', None),
        "analysis_summary": getattr(evidence, 'analysis_summary', None),
        "analysis_findings": getattr(evidence, 'analysis_findings', None),
        "risk_indicators": getattr(evidence, 'risk_indicators', None),
        "extract_metadata": evidence.extract_metadata,
        "extracted_text_preview": (evidence.extracted_text or "")[:500] if not has_analysis else None,
        "enrichment_pending": not has_analysis,
        "last_enriched_at": str(evidence.last_enriched_at) if evidence.last_enriched_at else None,
    }


@router.post("/{evidence_id}/analyze")
def analyze_evidence_file(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Trigger Bedrock analysis on a single evidence file without running full
    assessment enrichment. Uses document-type-specific prompts.
    """
    tenant_id, _ = context

    from ..models.models import Assessment, ThreatCatalogue
    from ..services.intelligence_service import intelligence_service

    evidence = EvidenceService.get_evidence(db=db, evidence_id=evidence_id, tenant_id=tenant_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    if evidence.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evidence is not ready for analysis (status: {evidence.status})"
        )

    if not evidence.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence has no extracted text to analyze"
        )

    assessment = db.query(Assessment).filter(
        Assessment.id == evidence.assessment_id,
        Assessment.tenant_id == tenant_id,
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # Build catalogue summary
    catalogue_threats = db.query(ThreatCatalogue).filter(
        ThreatCatalogue.tenant_id == tenant_id,
        ThreatCatalogue.is_active == True,
    ).all()

    catalogue_summary = "\n".join([
        f"- catalogue_key: {t.catalogue_key}, name: {t.name}, category: {t.category or 'General'}"
        for t in catalogue_threats[:20]
    ]) if catalogue_threats else "No threat catalogue available"

    try:
        findings = intelligence_service._analyze_evidence_file(
            evidence, assessment, catalogue_summary
        )

        # Stamp enrichment time
        from datetime import datetime
        evidence.last_enriched_at = datetime.utcnow()
        db.commit()

        return {
            "evidence_id": str(evidence.id),
            "file_name": evidence.file_name,
            "document_type": evidence.document_type,
            "analysis_summary": getattr(evidence, 'analysis_summary', None),
            "analysis_findings": getattr(evidence, 'analysis_findings', None),
            "risk_indicators": getattr(evidence, 'risk_indicators', None),
            "findings_count": len(findings),
            "status": "analyzed",
        }
    except Exception as e:
        logger.error(f"Error analyzing evidence {evidence_id}: {e}")
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
