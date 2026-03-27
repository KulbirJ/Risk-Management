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
        """Service health check — includes DB ping and Bedrock config status."""
        from sqlalchemy import text
        from .db.database import SessionLocal
        from .services.bedrock_service import BedrockService

        checks: dict = {"version": settings.app_version}

        # DB ping
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            checks["db"] = "ok"
        except Exception as exc:
            checks["db"] = f"error: {exc}"

        # Bedrock config (does NOT make a live call — use /intelligence/bedrock-test for that)
        try:
            bedrock = BedrockService()
            checks["bedrock"] = {
                "enabled": bedrock.enabled,
                "model_id": bedrock.model_id,
                "region": bedrock.region,
                "client_initialized": bedrock.client is not None,
            }
        except Exception as exc:
            checks["bedrock"] = {"enabled": False, "error": str(exc)}

        overall = "healthy" if checks["db"] == "ok" else "degraded"
        return {"status": overall, **checks}
    
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
            Recommendation, ActiveRisk, AuditLog, ThreatCatalogue, IntelligenceJob,
            AttackTactic, AttackTechnique, ThreatAttackMapping,
            KillChain, KillChainStage, AttackSyncStatus,
            ThreatIntelEnrichment, AttackGroup,
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
                ("assessments", "industry_sector", "VARCHAR(50)"),
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
                ("threats", "intel_enriched", "BOOLEAN DEFAULT FALSE"),
                ("threats", "likelihood_score_rationale", "JSONB DEFAULT '{}'"),
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
                ("evidence", "document_type_confidence", "INTEGER"),
                ("evidence", "analysis_summary", "TEXT"),
                ("evidence", "analysis_findings", "JSONB"),
                ("evidence", "risk_indicators", "JSONB"),
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
                ("active_risks", "next_review_date", "TIMESTAMP WITH TIME ZONE"),
                ("active_risks", "estimated_persistence_days", "INTEGER"),
                ("active_risks", "score_locked", "BOOLEAN DEFAULT FALSE"),
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
                
                # ============ ATTACK_TACTICS TABLE (MITRE ATT&CK) ============
                ("attack_tactics", "stix_id", "VARCHAR(255)"),
                ("attack_tactics", "mitre_id", "VARCHAR(50)"),
                ("attack_tactics", "name", "VARCHAR(255)"),
                ("attack_tactics", "shortname", "VARCHAR(100)"),
                ("attack_tactics", "description", "TEXT"),
                ("attack_tactics", "url", "VARCHAR(512)"),
                ("attack_tactics", "phase_order", "INTEGER"),
                ("attack_tactics", "last_synced_at", "TIMESTAMP WITH TIME ZONE"),
                ("attack_tactics", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ ATTACK_TECHNIQUES TABLE ============
                ("attack_techniques", "stix_id", "VARCHAR(255)"),
                ("attack_techniques", "mitre_id", "VARCHAR(50)"),
                ("attack_techniques", "name", "VARCHAR(255)"),
                ("attack_techniques", "tactic_shortname", "VARCHAR(100)"),
                ("attack_techniques", "description", "TEXT"),
                ("attack_techniques", "detection_text", "TEXT"),
                ("attack_techniques", "platforms", "JSONB DEFAULT '[]'"),
                ("attack_techniques", "data_sources", "JSONB DEFAULT '[]'"),
                ("attack_techniques", "mitigations", "JSONB DEFAULT '[]'"),
                ("attack_techniques", "url", "VARCHAR(512)"),
                ("attack_techniques", "is_subtechnique", "BOOLEAN DEFAULT FALSE"),
                ("attack_techniques", "is_deprecated", "BOOLEAN DEFAULT FALSE"),
                ("attack_techniques", "last_synced_at", "TIMESTAMP WITH TIME ZONE"),
                ("attack_techniques", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ THREAT_ATTACK_MAPPINGS TABLE ============
                ("threat_attack_mappings", "confidence_score", "INTEGER DEFAULT 70"),
                ("threat_attack_mappings", "auto_mapped", "BOOLEAN DEFAULT FALSE"),
                ("threat_attack_mappings", "mapping_rationale", "TEXT"),
                ("threat_attack_mappings", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ KILL_CHAINS TABLE ============
                ("kill_chains", "scenario_name", "VARCHAR(255)"),
                ("kill_chains", "description", "TEXT"),
                ("kill_chains", "threat_actor", "VARCHAR(255)"),
                ("kill_chains", "generated_by_ai", "BOOLEAN DEFAULT TRUE"),
                ("kill_chains", "model_id", "VARCHAR(255)"),
                ("kill_chains", "status", "VARCHAR(50) DEFAULT 'complete'"),
                ("kill_chains", "error_message", "TEXT"),
                ("kill_chains", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ KILL_CHAIN_STAGES TABLE ============
                ("kill_chain_stages", "stage_number", "INTEGER"),
                ("kill_chain_stages", "tactic_name", "VARCHAR(100)"),
                ("kill_chain_stages", "technique_name", "VARCHAR(255)"),
                ("kill_chain_stages", "mitre_id", "VARCHAR(50)"),
                ("kill_chain_stages", "description", "TEXT"),
                ("kill_chain_stages", "actor_behavior", "TEXT"),
                ("kill_chain_stages", "detection_hint", "TEXT"),
                ("kill_chain_stages", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ ATTACK_SYNC_STATUS TABLE ============
                ("attack_sync_status", "sync_status", "VARCHAR(50) DEFAULT 'never'"),
                ("attack_sync_status", "last_synced_at", "TIMESTAMP WITH TIME ZONE"),
                ("attack_sync_status", "tactics_count", "INTEGER DEFAULT 0"),
                ("attack_sync_status", "techniques_count", "INTEGER DEFAULT 0"),
                ("attack_sync_status", "source_url", "VARCHAR(512)"),
                ("attack_sync_status", "error_message", "TEXT"),
                ("attack_sync_status", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("attack_sync_status", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ THREAT_INTEL_ENRICHMENTS TABLE (Phase 1) ============
                ("threat_intel_enrichments", "source", "VARCHAR(50) NOT NULL"),
                ("threat_intel_enrichments", "source_id", "VARCHAR(255)"),
                ("threat_intel_enrichments", "raw_data", "JSONB DEFAULT '{}'"),
                ("threat_intel_enrichments", "feature_vector", "JSONB DEFAULT '{}'"),
                ("threat_intel_enrichments", "severity_score", "INTEGER"),
                ("threat_intel_enrichments", "fetched_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("threat_intel_enrichments", "expires_at", "TIMESTAMP WITH TIME ZONE"),
                ("threat_intel_enrichments", "is_stale", "BOOLEAN DEFAULT FALSE"),
                
                # ============ ATTACK_GROUPS TABLE (Phase 1) ============
                ("attack_groups", "stix_id", "VARCHAR(255)"),
                ("attack_groups", "name", "VARCHAR(255)"),
                ("attack_groups", "aliases", "JSONB DEFAULT '[]'"),
                ("attack_groups", "description", "TEXT"),
                ("attack_groups", "technique_ids", "JSONB DEFAULT '[]'"),
                ("attack_groups", "target_sectors", "JSONB DEFAULT '[]'"),
                ("attack_groups", "first_seen", "VARCHAR(50)"),
                ("attack_groups", "last_seen", "VARCHAR(50)"),
                ("attack_groups", "url", "VARCHAR(512)"),
                ("attack_groups", "last_synced_at", "TIMESTAMP WITH TIME ZONE"),
                ("attack_groups", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ COMPLIANCE_FRAMEWORKS TABLE ============
                ("compliance_frameworks", "key", "VARCHAR(100)"),
                ("compliance_frameworks", "name", "VARCHAR(255)"),
                ("compliance_frameworks", "version", "VARCHAR(50)"),
                ("compliance_frameworks", "description", "TEXT"),
                ("compliance_frameworks", "is_active", "BOOLEAN DEFAULT TRUE"),
                ("compliance_frameworks", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("compliance_frameworks", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ COMPLIANCE_CONTROLS TABLE ============
                ("compliance_controls", "framework_id", "UUID REFERENCES compliance_frameworks(id)"),
                ("compliance_controls", "control_id", "VARCHAR(50)"),
                ("compliance_controls", "title", "VARCHAR(255)"),
                ("compliance_controls", "description", "TEXT"),
                ("compliance_controls", "family", "VARCHAR(100)"),
                ("compliance_controls", "priority", "VARCHAR(20)"),
                ("compliance_controls", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                
                # ============ COMPLIANCE_MAPPINGS TABLE ============
                ("compliance_mappings", "control_id", "UUID REFERENCES compliance_controls(id)"),
                ("compliance_mappings", "threat_id", "UUID REFERENCES threats(id)"),
                ("compliance_mappings", "assessment_id", "UUID REFERENCES assessments(id)"),
                ("compliance_mappings", "status", "VARCHAR(30) DEFAULT 'not_assessed'"),
                ("compliance_mappings", "notes", "TEXT"),
                ("compliance_mappings", "evidence_ids", "JSONB DEFAULT '[]'"),
                ("compliance_mappings", "mapped_by", "VARCHAR(20) DEFAULT 'manual'"),
                ("compliance_mappings", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ("compliance_mappings", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
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
    from .api import assessments, threats, evidence, recommendations, active_risks, audit_logs, intelligence, attack, intel, compliance
    
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
    app.include_router(
        attack.router,
        prefix="/api/v1/attack",
        tags=["attack"]
    )
    app.include_router(
        intel.router,
        prefix="/api/v1/intel",
        tags=["intel"]
    )
    app.include_router(
        compliance.router,
        prefix="/api/v1/compliance",
        tags=["compliance"]
    )

    # ML routers — only loaded when numpy/scikit-learn/networkx are available
    try:
        from .api import ml, graph, clusters
        app.include_router(
            ml.router,
            prefix="/api/v1/ml",
            tags=["ml"]
        )
        app.include_router(
            graph.router,
            prefix="/api/v1/graph",
            tags=["graph"]
        )
        app.include_router(
            clusters.router,
            prefix="/api/v1/clusters",
            tags=["clusters"]
        )
        logger.info("ML/Graph/Cluster routers loaded successfully")
    except ImportError as e:
        logger.warning(f"ML routers not loaded (missing dependencies): {e}")
    
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
            tenant_id=tenant_id,
            job_id=job_id,
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

    def _handle_run_migrations(event):
        """Run database schema migrations via direct Lambda invocation."""
        import logging
        import traceback
        _logger = logging.getLogger(__name__)
        _logger.info("[MIGRATE] Running schema migrations...")
        try:
            from sqlalchemy import text, inspect as sa_inspect
            from .db.database import SessionLocal, engine, Base
            from .models import models as _models  # noqa: F841 — ensure all models loaded

            db = SessionLocal()
            results = []
            try:
                Base.metadata.create_all(bind=engine)
                results.append("Created any missing tables")

                inspector = sa_inspect(engine)
                # Comprehensive column list — mirrors /migrate-schema endpoint
                schema_updates = [
                    ("assessments", "industry_sector", "VARCHAR(50)"),
                    ("threats", "intel_enriched", "BOOLEAN DEFAULT FALSE"),
                    ("threats", "likelihood_score_rationale", "JSONB DEFAULT '{}'"),
                    ("active_risks", "next_review_date", "TIMESTAMP WITH TIME ZONE"),
                    ("active_risks", "estimated_persistence_days", "INTEGER"),
                    ("active_risks", "score_locked", "BOOLEAN DEFAULT FALSE"),
                    # Evidence analysis columns
                    ("evidence", "document_type_confidence", "INTEGER"),
                    ("evidence", "analysis_summary", "TEXT"),
                    ("evidence", "analysis_findings", "JSONB"),
                    ("evidence", "risk_indicators", "JSONB"),
                    # Stage 1 outcome tracking columns
                    ("active_risks", "outcome", "VARCHAR(50)"),
                    ("active_risks", "outcome_recorded_at", "TIMESTAMP WITH TIME ZONE"),
                    ("active_risks", "outcome_severity", "VARCHAR(20)"),
                    ("active_risks", "days_to_resolution", "INTEGER"),
                    ("active_risks", "false_positive", "BOOLEAN DEFAULT FALSE"),
                    # Compliance framework tables
                    ("compliance_frameworks", "key", "VARCHAR(100)"),
                    ("compliance_frameworks", "name", "VARCHAR(255)"),
                    ("compliance_frameworks", "version", "VARCHAR(50)"),
                    ("compliance_frameworks", "description", "TEXT"),
                    ("compliance_frameworks", "is_active", "BOOLEAN DEFAULT TRUE"),
                    ("compliance_frameworks", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                    ("compliance_frameworks", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                    ("compliance_controls", "framework_id", "UUID REFERENCES compliance_frameworks(id)"),
                    ("compliance_controls", "control_id", "VARCHAR(50)"),
                    ("compliance_controls", "title", "VARCHAR(255)"),
                    ("compliance_controls", "description", "TEXT"),
                    ("compliance_controls", "family", "VARCHAR(100)"),
                    ("compliance_controls", "priority", "VARCHAR(20)"),
                    ("compliance_controls", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                    ("compliance_mappings", "control_id", "UUID REFERENCES compliance_controls(id)"),
                    ("compliance_mappings", "threat_id", "UUID REFERENCES threats(id)"),
                    ("compliance_mappings", "assessment_id", "UUID REFERENCES assessments(id)"),
                    ("compliance_mappings", "status", "VARCHAR(30) DEFAULT 'not_assessed'"),
                    ("compliance_mappings", "notes", "TEXT"),
                    ("compliance_mappings", "evidence_ids", "JSONB DEFAULT '[]'"),
                    ("compliance_mappings", "mapped_by", "VARCHAR(20) DEFAULT 'manual'"),
                    ("compliance_mappings", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                    ("compliance_mappings", "updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
                ]
                for table, column, col_type in schema_updates:
                    existing = [c["name"] for c in inspector.get_columns(table)]
                    if column not in existing:
                        db.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{column}" {col_type}'))
                        results.append(f"Added {table}.{column}")
                db.commit()
                results.append("Schema sync completed")
            finally:
                db.close()

            _logger.info(f"[MIGRATE] Done: {results}")
            return {"statusCode": 200, "body": "Migrations completed", "results": results}
        except Exception as e:
            _logger.error(f"[MIGRATE] FAILED: {e}\n{traceback.format_exc()}")
            return {"statusCode": 500, "body": f"Migration failed: {e}"}

    def _handle_full_assessment_run(event):
        """
        Lambda action: run_full_assessment
        Runs the complete risk-assessment pipeline for one assessment:
          AI enrichment → intel → ML scoring → clustering → ATT&CK mapping → kill chains
        Progress is written to IntelligenceJob.results so the frontend can poll it.
        """
        import traceback
        import logging
        _logger = logging.getLogger(__name__)
        _logger.setLevel(logging.INFO)

        job_id       = event["job_id"]
        assessment_id = event["assessment_id"]
        tenant_id    = event["tenant_id"]
        user_id      = event["user_id"]

        _logger.info("[FULL_RUN] Lambda handler invoked: job=%s", job_id)
        try:
            from .db.database import SessionLocal
            from .services.full_run_service import run_full_assessment_pipeline
            from .models.models import IntelligenceJob
            from datetime import datetime

            db = SessionLocal()
            try:
                return run_full_assessment_pipeline(
                    db=db,
                    job_id=job_id,
                    assessment_id=assessment_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            finally:
                db.close()
        except Exception as exc:
            _logger.error("[FULL_RUN] Fatal error: %s\n%s", exc, traceback.format_exc())
            # Best-effort: mark the job as failed so it doesn't stay stuck at "running"
            try:
                from .db.database import SessionLocal
                from .models.models import IntelligenceJob
                _db = SessionLocal()
                try:
                    _job = _db.query(IntelligenceJob).filter(IntelligenceJob.id == job_id).first()
                    if _job and _job.status in ("pending", "running"):
                        _job.status = "failed"
                        _job.error_message = f"Fatal pipeline error: {str(exc)[:500]}"
                        _job.completed_at = datetime.utcnow()
                        _db.commit()
                finally:
                    _db.close()
            except Exception:
                pass
            return {"statusCode": 500, "body": f"Full assessment run failed: {exc}"}

    def lambda_handler(event, context):
        """Route Lambda events: migrations, async enrichment, full run, or API Gateway via Mangum."""
        if isinstance(event, dict):
            action = event.get("action", "")
            if action == "enrich_assessment":
                return _handle_async_enrichment(event)
            if action == "run_full_assessment":
                return _handle_full_assessment_run(event)
            if action in ("run_migrations", "migrate"):
                return _handle_run_migrations(event)
            if action == "retrain_ml_model":
                return _handle_ml_retrain(event)
            # EventBridge scheduled event (source = "aws.events")
            if event.get("source") == "aws.events" and "retrain" in str(event.get("detail-type", "")).lower():
                return _handle_ml_retrain(event)
        return _mangum_handler(event, context)

    def _handle_ml_retrain(event):
        """
        Stage 4 — Scheduled / on-demand ML retraining handler.

        Invoked by:
          - EventBridge cron (every Sunday 3AM UTC)
          - Manual: POST /ml/train
          - Direct Lambda invoke: {"action": "retrain_ml_model"}

        Quality gates:
          1. Requires ≥ 10 enriched threats (configurable via min_samples).
          2. Saves to S3 candidate/ only — NOT auto-promoted.
          3. Sends SNS notification if ML_RETRAIN_SNS_TOPIC env var is set.
        """
        import logging
        import os
        import json
        import traceback
        _logger = logging.getLogger(__name__)
        _logger.info("[ML_RETRAIN] Starting scheduled retraining...")

        algorithm = event.get("algorithm", "random_forest")
        min_samples = int(event.get("min_samples", 10))
        auto_promote = bool(event.get("auto_promote", False))

        try:
            from .db.database import SessionLocal
            from .services.ml.scoring_service import MLScoringService
            from uuid import UUID as _UUID
            from .core.config import settings as _cfg

            TENANT_ID = "67636bd3-9846-4bde-806f-aea369fc9457"

            db = SessionLocal()
            result = {}
            try:
                svc = MLScoringService()
                result = svc.train(
                    db,
                    _UUID(TENANT_ID),
                    algorithm=algorithm,
                    min_samples=min_samples,
                )
            finally:
                db.close()

            _logger.info("[ML_RETRAIN] Training result: %s", result)

            # Auto-promote if caller requested AND accuracy improved
            if auto_promote and result.get("trained"):
                promote_result = svc.promote_model()
                result["promotion"] = promote_result
                _logger.info("[ML_RETRAIN] Promotion result: %s", promote_result)

            # Optional SNS notification
            sns_topic = os.environ.get("ML_RETRAIN_SNS_TOPIC")
            if sns_topic and result.get("trained"):
                try:
                    import boto3
                    sns = boto3.client("sns", region_name=_cfg.aws_region)
                    accuracy = result.get("metrics", {}).get("cv_accuracy_mean", 0)
                    promoted = result.get("promotion", {}).get("promoted", False)
                    msg = (
                        f"ML Model Retraining Complete\n"
                        f"Algorithm: {algorithm}\n"
                        f"Samples: {result.get('n_samples', 0)}\n"
                        f"Accuracy: {accuracy:.4f}\n"
                        f"Real outcomes: {result.get('using_real_outcomes', False)}\n"
                        f"Candidate saved to S3: {result.get('s3_candidate', 'N/A')}\n"
                        f"Auto-promoted: {promoted}\n"
                        f"Action needed: {'None' if promoted else 'Review candidate and call POST /ml/promote-model if satisfied'}"
                    )
                    sns.publish(TopicArn=sns_topic, Subject="[Compliance Platform] ML Model Retrained", Message=msg)
                    _logger.info("[ML_RETRAIN] SNS notification sent")
                except Exception as _sns_err:
                    _logger.warning("[ML_RETRAIN] SNS notification failed: %s", _sns_err)

            return {"statusCode": 200, "body": json.dumps(result)}

        except Exception as e:
            _logger.error("[ML_RETRAIN] FAILED: %s\n%s", e, traceback.format_exc())
            return {"statusCode": 500, "body": f"ML retraining failed: {e}"}

except ImportError:
    # Mangum not installed, likely running locally
    lambda_handler = None
