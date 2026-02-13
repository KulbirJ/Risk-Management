"""Intelligence API router endpoints for AI enrichment."""
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas.schemas import (
    IntelligenceEnrichRequest,
    IntelligenceEnrichResponse,
    IntelligenceJobRead,
    IntelligenceStatusResponse
)
from ..services.intelligence_service import intelligence_service
from ..models.models import IntelligenceJob, Assessment, ThreatCatalogue
from ..core.config import settings

router = APIRouter()


def get_tenant_context(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> tuple[UUID, UUID]:
    """Extract tenant and user context from headers."""
    return x_tenant_id, x_user_id


def _run_enrichment_job(
    job_id: str,
    assessment_id: str,
    tenant_id: str,
    db_url: str
):
    """Background task to run enrichment job."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Update job status to running
        job = db.query(IntelligenceJob).filter(IntelligenceJob.id == job_id).first()
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

        # Run enrichment
        results = intelligence_service.enrich_assessment(
            db=db,
            assessment_id=assessment_id,
            tenant_id=tenant_id
        )

        # Update job with results
        if job:
            job.status = results.get("status", "completed")
            job.completed_at = datetime.utcnow()
            job.results = results
            job.model_id = settings.bedrock_model_id
            if results.get("errors"):
                job.error_message = "; ".join(results["errors"][:5])
            db.commit()

    except Exception as e:
        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/status", response_model=IntelligenceStatusResponse)
def get_intelligence_status():
    """Check the status and configuration of the intelligence service."""
    return IntelligenceStatusResponse(
        bedrock_enabled=settings.bedrock_enabled,
        primary_model=settings.bedrock_model_id,
        fallback_model=settings.bedrock_fallback_model_id,
        bedrock_region=settings.bedrock_region,
        confidence_threshold=settings.intelligence_confidence_threshold
    )


@router.post("/enrich", response_model=IntelligenceEnrichResponse, status_code=status.HTTP_202_ACCEPTED)
def enrich_assessment(
    request: IntelligenceEnrichRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """
    Trigger AI enrichment for an assessment.
    
    This starts a background job that:
    1. Extracts vulnerabilities from the assessment description
    2. Maps threats from the threat catalogue
    3. Calculates risk scores
    4. Generates mitigation recommendations
    """
    tenant_id, user_id = context

    if not settings.bedrock_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service is not enabled. Set BEDROCK_ENABLED=True."
        )

    # Verify assessment exists and belongs to tenant
    assessment = db.query(Assessment).filter(
        Assessment.id == request.assessment_id,
        Assessment.tenant_id == tenant_id
    ).first()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment {request.assessment_id} not found"
        )

    # Check for existing running jobs
    existing_job = db.query(IntelligenceJob).filter(
        IntelligenceJob.assessment_id == request.assessment_id,
        IntelligenceJob.status.in_(["pending", "running"])
    ).first()

    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An enrichment job is already running for this assessment (job: {existing_job.id})"
        )

    # Create intelligence job record
    job = IntelligenceJob(
        tenant_id=tenant_id,
        assessment_id=request.assessment_id,
        initiated_by_id=user_id,
        status="pending",
        job_type=request.job_type,
        model_id=settings.bedrock_model_id
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Run enrichment in background
    background_tasks.add_task(
        _run_enrichment_job,
        job_id=str(job.id),
        assessment_id=str(request.assessment_id),
        tenant_id=str(tenant_id),
        db_url=settings.database_url
    )

    return IntelligenceEnrichResponse(
        job_id=job.id,
        assessment_id=request.assessment_id,
        status="pending",
        model_used=settings.bedrock_model_id,
        started_at=None,
        completed_at=None
    )


@router.get("/jobs", response_model=List[IntelligenceJobRead])
def list_intelligence_jobs(
    assessment_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """List intelligence jobs for the tenant."""
    tenant_id, user_id = context

    query = db.query(IntelligenceJob).filter(
        IntelligenceJob.tenant_id == tenant_id
    )

    if assessment_id:
        query = query.filter(IntelligenceJob.assessment_id == assessment_id)
    if status:
        query = query.filter(IntelligenceJob.status == status)

    jobs = query.order_by(IntelligenceJob.created_at.desc()).limit(limit).all()

    return [IntelligenceJobRead.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=IntelligenceJobRead)
def get_intelligence_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """Get a specific intelligence job by ID."""
    tenant_id, user_id = context

    job = db.query(IntelligenceJob).filter(
        IntelligenceJob.id == job_id,
        IntelligenceJob.tenant_id == tenant_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intelligence job {job_id} not found"
        )

    return IntelligenceJobRead.model_validate(job)


@router.post("/seed-catalogue")
def seed_threat_catalogue(
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    """Seed the threat catalogue with standard threat entries."""
    tenant_id, user_id = context

    threats = [
        {"catalogue_key": "malicious_code", "name": "Malicious Code/Software", "category": "Application",
         "description": "Code in any part of a software system intended to cause undesired effects or damage, includes attack scripts, backdoors and malicious active content."},
        {"catalogue_key": "social_engineering_phishing", "name": "Social Engineering (Phishing)", "category": "Human",
         "description": "Phishing scams are fraudulent attempts by cybercriminals to obtain private information."},
        {"catalogue_key": "mitm_eavesdropping", "name": "Man-in-the-middle attack/Eavesdropping", "category": "Network",
         "description": "A type of cyberattack where a malicious actor intercepts a conversation between two parties and gains access to information."},
        {"catalogue_key": "password_cracking", "name": "Password Cracking/Credential Management", "category": "Access",
         "description": "The process of using various techniques to discover computer passwords or stealing computer-based information."},
        {"catalogue_key": "system_penetration_hacking", "name": "System Penetration/Hacking", "category": "Infrastructure",
         "description": "An attempt to gain unauthorized access to the IT infrastructure by trying to exploit vulnerabilities."},
        {"catalogue_key": "dos_disruption", "name": "Denial of Service/Disruption", "category": "Network",
         "description": "Partial or complete outage of service, termination of contract or forces of nature."},
        {"catalogue_key": "unauthorized_access", "name": "Unauthorized Access", "category": "Access",
         "description": "When someone gains access to a website, program, server, service, or other system using someone else's account."},
        {"catalogue_key": "data_loss_leakage", "name": "Data Loss/Data Leakage", "category": "Data",
         "description": "An error condition where information is destroyed by failures or neglect in storage, transmission, or processing."},
        {"catalogue_key": "insider_threats", "name": "Insider Threats", "category": "Human",
         "description": "Individuals within the organization who intentionally or unintentionally pose a risk to systems or data."},
        {"catalogue_key": "supply_chain_attacks", "name": "Supply Chain Attacks", "category": "Infrastructure",
         "description": "Compromising a system through vulnerabilities in third-party vendors, partners, or software/hardware suppliers."},
        {"catalogue_key": "apt", "name": "Advanced Persistent Threats (APTs)", "category": "Application",
         "description": "Sophisticated, targeted attacks by state-sponsored or highly skilled adversary groups that persist in a network for extended periods."},
        {"catalogue_key": "ransomware", "name": "Ransomware", "category": "Application",
         "description": "Malware that encrypts files/systems and demands payment for decryption. May include data exfiltration threats."},
        {"catalogue_key": "zero_day", "name": "Zero-Day Exploits", "category": "Application",
         "description": "Attacks using vulnerabilities unknown to the software vendor with no patches available."},
        {"catalogue_key": "web_app_attacks", "name": "Web Application Attacks", "category": "Application",
         "description": "Such as SQL injection, cross-site scripting (XSS), and cross-site request forgery (CSRF) targeting web-based applications."},
        {"catalogue_key": "physical_breach", "name": "Physical Security Breaches", "category": "Physical",
         "description": "Unauthorized physical access to infrastructure that could compromise IT assets or data."},
        {"catalogue_key": "malware_removable_media", "name": "Malware Loaded Removable Media", "category": "Physical",
         "description": "Attacks via infected USB drives or portable storage devices introduced into secure environments."},
        {"catalogue_key": "misconfiguration", "name": "Misconfiguration and Weak Security Controls", "category": "Infrastructure",
         "description": "Poorly configured systems, default credentials, or inadequate policies leading to vulnerabilities."},
        {"catalogue_key": "cloud_security", "name": "Cloud Security Threats", "category": "Infrastructure",
         "description": "Risks associated with cloud infrastructure such as misconfigured cloud storage, account hijacking, or insecure APIs."},
        {"catalogue_key": "iot_ot_threats", "name": "IoT and OT System Threats", "category": "Infrastructure",
         "description": "Vulnerabilities and attacks targeting Internet-of-Things devices and operational technology environments."},
    ]

    created = 0
    skipped = 0
    for threat_data in threats:
        existing = db.query(ThreatCatalogue).filter(
            ThreatCatalogue.catalogue_key == threat_data["catalogue_key"]
        ).first()
        if existing:
            skipped += 1
            continue

        entry = ThreatCatalogue(
            tenant_id=tenant_id,
            catalogue_key=threat_data["catalogue_key"],
            name=threat_data["name"],
            title=threat_data["name"],
            category=threat_data["category"],
            description=threat_data["description"],
            default_likelihood="Medium",
            default_impact="Medium",
            mitigations=[],
            is_active=True
        )
        db.add(entry)
        created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "total": len(threats)}
