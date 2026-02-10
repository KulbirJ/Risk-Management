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
            Recommendation, ActiveRisk, AuditLog, ThreatCatalogue
        )
        
        db = SessionLocal()
        results = []
        try:
            # First, create all tables that don't exist
            Base.metadata.create_all(bind=engine)
            results.append("Created any missing tables")
            
            # Get inspector to check existing columns
            inspector = inspect(engine)
            
            # Define all columns that should exist per table
            schema_updates = [
                # active_risks table
                ("active_risks", "risk_status", "VARCHAR(50) DEFAULT 'Planned'"),
                ("active_risks", "status", "VARCHAR(50) DEFAULT 'open'"),
                ("active_risks", "mitigation_plan", "TEXT"),
                ("active_risks", "acceptance_date", "TIMESTAMP WITH TIME ZONE"),
                ("active_risks", "review_cycle_days", "INTEGER DEFAULT 30"),
                
                # threats table
                ("threats", "likelihood_score", "INTEGER DEFAULT 0"),
                ("threats", "ai_rationale", "TEXT"),
                ("threats", "cve_ids", "JSONB DEFAULT '[]'"),
                ("threats", "cvss_score", "VARCHAR(10)"),
                
                # assessments table
                ("assessments", "system_background", "TEXT"),
                ("assessments", "scope", "TEXT"),
                ("assessments", "tech_stack", "JSONB DEFAULT '[]'"),
                ("assessments", "overall_impact", "VARCHAR(20) DEFAULT 'Medium'"),
                
                # users table
                ("users", "cognito_sub", "VARCHAR(255)"),
                ("users", "roles", "JSONB DEFAULT '[\"viewer\"]'"),
                ("users", "is_active", "BOOLEAN DEFAULT TRUE"),
                ("users", "last_login", "TIMESTAMP WITH TIME ZONE"),
                
                # tenants table
                ("tenants", "region", "VARCHAR(50) DEFAULT 'ca-west-1'"),
                ("tenants", "settings", "JSONB DEFAULT '{}'"),
                
                # recommendations table
                ("recommendations", "confidence_score", "INTEGER DEFAULT 0"),
                ("recommendations", "target_date", "TIMESTAMP WITH TIME ZONE"),
                
                # evidence table
                ("evidence", "mime_type", "VARCHAR(100)"),
                ("evidence", "file_size_bytes", "BIGINT"),
                ("evidence", "storage_path", "VARCHAR(512)"),
                
                # audit_logs table
                ("audit_logs", "ip_address", "VARCHAR(50)"),
                ("audit_logs", "user_agent", "VARCHAR(512)"),
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
            
            return {"status": "success", "results": results}
        except Exception as e:
            db.rollback()
            import traceback
            return {"status": "error", "message": str(e), "trace": traceback.format_exc()}
        finally:
            db.close()
    
    # Include API routers
    from .api import assessments, threats, evidence, recommendations, active_risks, audit_logs
    
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
    
    # Future routers (Phase 2+)
    # from .api import threat_catalogue
    # app.include_router(threat_catalogue.router, prefix="/api/v1/threat-catalogue", tags=["threat-catalogue"])
    
    return app


app = create_app()

# AWS Lambda handler
try:
    from mangum import Mangum
    # Configure Mangum for Lambda with optimizations
    lambda_handler = Mangum(
        app,
        lifespan="off",  # Disable lifespan for Lambda cold starts
        api_gateway_base_path="/",  # API Gateway stage path
    )
except ImportError:
    # Mangum not installed, likely running locally
    lambda_handler = None
