"""FastAPI application factory and startup/shutdown."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .db.database import engine, Base

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting Compliance Platform MVP - Phase 0")
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Compliance Platform MVP")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Cybersecurity Risk Assessment Compliance Platform",
        debug=settings.debug,
    )
    
    # Add CORS middleware with explicit wildcard for all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for testing
        allow_credentials=False,  # Must be False when using wildcard
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Service health check."""
        return {"status": "healthy", "version": settings.app_version}
    
    # Seed endpoint for database initialization
    @app.post("/seed")
    async def seed_database():
        """Seed database with test tenant and user."""
        from sqlalchemy.orm import Session
        from .db.database import SessionLocal
        from .models.models import Tenant, User
        import uuid
        
        db: Session = SessionLocal()
        try:
            tenant_id = uuid.UUID("67636bd3-9846-4bde-806f-aea369fc9457")
            user_id = uuid.UUID("0bc9d6a9-f342-452e-9297-ee33f44d4f84")
            results = []
            
            # Check/create tenant
            existing_tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not existing_tenant:
                tenant = Tenant(
                    id=tenant_id,
                    name="Test Organization"
                )
                db.add(tenant)
                db.commit()
                results.append("Created test tenant")
            else:
                results.append("Test tenant already exists")
            
            # Check/create user
            existing_user = db.query(User).filter(User.id == user_id).first()
            if not existing_user:
                user = User(
                    id=user_id,
                    tenant_id=tenant_id,
                    email="testuser@testorg.com",
                    display_name="Test User",
                    roles=["admin"]
                )
                db.add(user)
                db.commit()
                results.append("Created test user")
            else:
                results.append("Test user already exists")
            
            return {"status": "success", "results": results}
        except Exception as e:
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    # Database migration endpoint - comprehensive schema sync
    @app.post("/migrate-schema")
    async def migrate_schema():
        """Sync database schema with models - creates tables and adds missing columns."""
        from sqlalchemy import text, inspect
        from .db.database import SessionLocal, engine, Base
        from .models.models import (
            Tenant, User, Assessment, Threat, Evidence,
            Recommendation, ActiveRisk, AuditLog, ThreatCatalogue, IntelligenceJob
        )
        
        db = SessionLocal()
        results = []
        try:
            # First, create all tables that don't exist
            Base.metadata.create_all(bind=engine)
            results.append("Created any missing tables")
            
            # Get inspector to check existing columns
            inspector = inspect(engine)
            
            # Define all columns that should exist per table (comprehensive list from models.py)
            schema_updates = [
                # ============ TENANTS TABLE ============
                ("tenants", "name", "VARCHAR(255)"),
                ("tenants", "region", "VARCHAR(50) DEFAULT 'ca-west-1'"),
                ("tenants", "settings", "JSONB DEFAULT '{}'"),
                ("tenants", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ USERS TABLE ============
                ("users", "email", "VARCHAR(255)"),
                ("users", "display_name", "VARCHAR(255)"),
                ("users", "cognito_sub", "VARCHAR(255)"),
                ("users", "roles", "JSONB DEFAULT '[\"viewer\"]'"),
                ("users", "is_active", "BOOLEAN DEFAULT TRUE"),
                ("users", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("users", "last_login", "TIMESTAMP WITH TIME ZONE"),
                
                # ============ ASSESSMENTS TABLE ============
                ("assessments", "title", "VARCHAR(255)"),
                ("assessments", "description", "TEXT"),
                ("assessments", "system_background", "TEXT"),
                ("assessments", "scope", "TEXT"),
                ("assessments", "tech_stack", "JSONB DEFAULT '[]'"),
                ("assessments", "overall_impact", "VARCHAR(20) DEFAULT 'Medium'"),
                ("assessments", "status", "VARCHAR(20) DEFAULT 'draft'"),
                ("assessments", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("assessments", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ THREATS TABLE ============
                ("threats", "catalogue_key", "VARCHAR(255)"),
                ("threats", "title", "VARCHAR(255)"),
                ("threats", "description", "TEXT"),
                ("threats", "recommendation", "TEXT"),
                ("threats", "detected_by", "VARCHAR(50) DEFAULT 'manual'"),
                ("threats", "cve_ids", "JSONB DEFAULT '[]'"),
                ("threats", "cvss_score", "VARCHAR(10)"),
                ("threats", "likelihood", "VARCHAR(20) DEFAULT 'Medium'"),
                ("threats", "likelihood_score", "INTEGER DEFAULT 0"),
                ("threats", "impact", "VARCHAR(20) DEFAULT 'Medium'"),
                ("threats", "severity", "VARCHAR(20) DEFAULT 'Medium'"),
                ("threats", "status", "VARCHAR(20) DEFAULT 'identified'"),
                ("threats", "ai_rationale", "TEXT"),
                ("threats", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("threats", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ EVIDENCE TABLE ============
                ("evidence", "s3_key", "VARCHAR(512)"),
                ("evidence", "file_name", "VARCHAR(255)"),
                ("evidence", "mime_type", "VARCHAR(100)"),
                ("evidence", "size_bytes", "INTEGER"),
                ("evidence", "status", "VARCHAR(50) DEFAULT 'processing'"),
                ("evidence", "extracted_text", "TEXT"),
                ("evidence", "extract_metadata", "JSONB"),
                ("evidence", "document_type", "VARCHAR(50)"),
                ("evidence", "quality", "VARCHAR(20) DEFAULT 'medium'"),
                ("evidence", "last_enriched_at", "TIMESTAMP WITH TIME ZONE"),
                ("evidence", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ RECOMMENDATIONS TABLE ============
                ("recommendations", "title", "VARCHAR(255)"),
                ("recommendations", "description", "TEXT"),
                ("recommendations", "text", "TEXT"),
                ("recommendations", "type", "VARCHAR(50) DEFAULT 'remediation'"),
                ("recommendations", "priority", "VARCHAR(20) DEFAULT 'Medium'"),
                ("recommendations", "status", "VARCHAR(50) DEFAULT 'open'"),
                ("recommendations", "target_date", "TIMESTAMP WITH TIME ZONE"),
                ("recommendations", "confidence_score", "INTEGER DEFAULT 0"),
                ("recommendations", "ai_generated", "BOOLEAN DEFAULT FALSE"),
                ("recommendations", "active_risk_id", "UUID REFERENCES active_risks(id)"),
                ("recommendations", "estimated_effort", "VARCHAR(20)"),
                ("recommendations", "cost_estimate", "VARCHAR(20)"),
                ("recommendations", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("recommendations", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ ACTIVE_RISKS TABLE ============
                ("active_risks", "title", "VARCHAR(255)"),
                ("active_risks", "risk_score", "INTEGER DEFAULT 50"),
                ("active_risks", "likelihood", "INTEGER DEFAULT 5"),
                ("active_risks", "impact", "INTEGER DEFAULT 5"),
                ("active_risks", "residual_risk", "VARCHAR(20) DEFAULT 'Medium'"),
                ("active_risks", "mitigation_plan", "TEXT"),
                ("active_risks", "acceptance_date", "TIMESTAMP WITH TIME ZONE"),
                ("active_risks", "review_cycle_days", "INTEGER DEFAULT 30"),
                ("active_risks", "status", "VARCHAR(50) DEFAULT 'open'"),
                ("active_risks", "risk_status", "VARCHAR(50) DEFAULT 'Planned'"),
                ("active_risks", "detected_by", "VARCHAR(50) DEFAULT 'manual'"),
                ("active_risks", "ai_rationale", "TEXT"),
                ("active_risks", "extra_data", "JSONB DEFAULT '{}'"),
                ("active_risks", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("active_risks", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ AUDIT_LOGS TABLE ============
                ("audit_logs", "action_type", "VARCHAR(255)"),
                ("audit_logs", "resource_type", "VARCHAR(100)"),
                ("audit_logs", "resource_id", "VARCHAR(255)"),
                ("audit_logs", "changes", "JSONB"),
                ("audit_logs", "ip_address", "VARCHAR(50)"),
                ("audit_logs", "user_agent", "VARCHAR(512)"),
                ("audit_logs", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ THREAT_CATALOGUE TABLE ============
                ("threat_catalogue", "catalogue_key", "VARCHAR(255)"),
                ("threat_catalogue", "name", "VARCHAR(255)"),
                ("threat_catalogue", "title", "VARCHAR(255)"),
                ("threat_catalogue", "category", "VARCHAR(100)"),
                ("threat_catalogue", "description", "TEXT"),
                ("threat_catalogue", "default_likelihood", "VARCHAR(20) DEFAULT 'Medium'"),
                ("threat_catalogue", "default_impact", "VARCHAR(20) DEFAULT 'Medium'"),
                ("threat_catalogue", "mitigations", "JSONB DEFAULT '[]'"),
                ("threat_catalogue", "is_active", "BOOLEAN DEFAULT TRUE"),
                ("threat_catalogue", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("threat_catalogue", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ INTELLIGENCE_JOBS TABLE ============
                ("intelligence_jobs", "status", "VARCHAR(50) DEFAULT 'pending'"),
                ("intelligence_jobs", "job_type", "VARCHAR(50) DEFAULT 'full_enrichment'"),
                ("intelligence_jobs", "model_id", "VARCHAR(255)"),
                ("intelligence_jobs", "started_at", "TIMESTAMP WITH TIME ZONE"),
                ("intelligence_jobs", "completed_at", "TIMESTAMP WITH TIME ZONE"),
                ("intelligence_jobs", "error_message", "TEXT"),
                ("intelligence_jobs", "results", "JSONB"),
                ("intelligence_jobs", "extra_data", "JSONB DEFAULT '{}'"),
                ("intelligence_jobs", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("intelligence_jobs", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ]
            
            for table_name, column_name, column_def in schema_updates:
                try:
                    # Check if table exists
                    if table_name in inspector.get_table_names():
                        existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
                        if column_name not in existing_columns:
                            db.execute(text(f"""
                                ALTER TABLE {table_name} 
                                ADD COLUMN IF NOT EXISTS {column_name} {column_def}
                            """))
                            results.append(f"Added {table_name}.{column_name}")
                except Exception as col_error:
                    results.append(f"Note: {table_name}.{column_name} - {str(col_error)[:50]}")
            
            db.commit()
            results.append("Schema sync completed")
            
            # Fix nullable constraints that may have been set incorrectly
            nullable_fixes = [
                ("active_risks", "title"),
                ("active_risks", "risk_owner_id"),
                ("recommendations", "assessment_id"),
                ("recommendations", "threat_id"),
            ]
            for table_name, column_name in nullable_fixes:
                try:
                    db.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP NOT NULL"))
                    results.append(f"Made {table_name}.{column_name} nullable")
                except Exception:
                    pass  # Already nullable or column doesn't exist
            db.commit()

            return {"status": "success", "results": results}
        except Exception as e:
            db.rollback()
            import traceback
            return {"status": "error", "message": str(e), "trace": traceback.format_exc()}
        finally:
            db.close()
    
    # One-time S3 CORS configuration endpoint
    @app.post("/configure-s3-cors")
    async def configure_s3_cors():
        """Set CORS policy on the evidence S3 bucket to allow browser uploads."""
        import boto3
        from botocore.exceptions import ClientError
        try:
            kwargs = {"region_name": settings.s3_bucket_region}
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                kwargs["aws_access_key_id"] = settings.aws_access_key_id
                kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            s3 = boto3.client("s3", **kwargs)

            cors_config = {
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "POST", "PUT", "HEAD"],
                        "AllowedOrigins": ["*"],
                        "ExposeHeaders": ["ETag", "x-amz-request-id"],
                        "MaxAgeSeconds": 3600,
                    }
                ]
            }
            s3.put_bucket_cors(
                Bucket=settings.s3_bucket_evidence,
                CORSConfiguration=cors_config,
            )
            return {"status": "success", "message": f"CORS configured on {settings.s3_bucket_evidence}"}
        except ClientError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # Include API routers
    from .api import assessments, threats, evidence, recommendations, active_risks, audit_logs, intelligence
    
    app.include_router(
        assessments.router,
        prefix="/api/v1/assessments",
        tags=["assessments"]
    )
    app.include_router(
        threats.router,
        prefix="/api/v1/threats",
        tags=["threats"]
    )
    app.include_router(
        evidence.router,
        prefix="/api/v1/evidence",
        tags=["evidence"]
    )
    app.include_router(
        recommendations.router,
        prefix="/api/v1/recommendations",
        tags=["recommendations"]
    )
    app.include_router(
        active_risks.router,
        prefix="/api/v1/active-risks",
        tags=["active-risks"]
    )
    app.include_router(
        audit_logs.router,
        prefix="/api/v1/audit-logs",
        tags=["audit-logs"]
    )
    app.include_router(
        intelligence.router,
        prefix="/api/v1/intelligence",
        tags=["intelligence"]
    )
    
    # Future routers (Phase 2+)
    # from .api import threat_catalogue
    # app.include_router(threat_catalogue.router, prefix="/api/v1/threat-catalogue", tags=["threat-catalogue"])
    
    return app


app = create_app()


def _handle_async_enrichment(event):
    """Handle async enrichment invoked via Lambda Event invocation."""
    import logging
    import traceback
    from datetime import datetime
    from .db.database import SessionLocal
    from .services.intelligence_service import intelligence_service
    from .models.models import IntelligenceJob

    _logger = logging.getLogger(__name__)
    _logger.setLevel(logging.INFO)

    job_id = event["job_id"]
    assessment_id = event["assessment_id"]
    tenant_id = event["tenant_id"]

    _logger.info(f"[ASYNC] Started job={job_id}, assessment={assessment_id}")

    db = SessionLocal()
    try:
        job = db.query(IntelligenceJob).filter(
            IntelligenceJob.id == job_id
        ).first()
        if not job:
            _logger.error(f"[ASYNC] Job {job_id} not found in DB")
            return {"status": "error", "message": "Job not found"}

        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        _logger.info(f"[ASYNC] Job {job_id} set to running, calling enrich_assessment")

        results = intelligence_service.enrich_assessment(
            db=db,
            assessment_id=assessment_id,
            tenant_id=tenant_id
        )

        _logger.info(f"[ASYNC] enrich_assessment returned: status={results.get('status')}, threats={results.get('threats_mapped')}")

        job.status = results.get("status", "completed")
        job.completed_at = datetime.utcnow()
        job.results = results
        if results.get("errors"):
            job.error_message = "; ".join(str(e) for e in results["errors"][:5])
        db.commit()

        _logger.info(f"[ASYNC] Job {job_id} completed: {job.status}")
        return {"status": job.status, "job_id": job_id}

    except Exception as e:
        _logger.error(f"[ASYNC] Job {job_id} FAILED: {e}\n{traceback.format_exc()}")
        try:
            if job:
                job.status = "failed"
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


# AWS Lambda handler
try:
    from mangum import Mangum
    # Configure Mangum for Lambda with optimizations
    _mangum_handler = Mangum(
        app,
        lifespan="off",  # Disable lifespan for Lambda cold starts
        api_gateway_base_path="/",  # API Gateway stage path
    )

    def lambda_handler(event, context):
        """Route Lambda events: async enrichment or API Gateway via Mangum."""
        if isinstance(event, dict) and event.get("action") == "enrich_assessment":
            return _handle_async_enrichment(event)
        return _mangum_handler(event, context)

except ImportError:
    # Mangum not installed, likely running locally
    lambda_handler = None
