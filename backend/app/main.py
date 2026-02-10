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
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
    
    # Database migration endpoint to add missing columns
    @app.post("/migrate-schema")
    async def migrate_schema():
        """Add missing columns to database schema."""
        from sqlalchemy import text
        from .db.database import SessionLocal
        
        db = SessionLocal()
        results = []
        try:
            # Add risk_status column to active_risks if it doesn't exist
            db.execute(text("""
                ALTER TABLE active_risks 
                ADD COLUMN IF NOT EXISTS risk_status VARCHAR(50) DEFAULT 'Planned'
            """))
            db.commit()
            results.append("Added risk_status column to active_risks (if missing)")
            
            return {"status": "success", "results": results}
        except Exception as e:
            db.rollback()
            return {"status": "error", "message": str(e)}
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
