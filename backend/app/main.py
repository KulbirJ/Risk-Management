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
