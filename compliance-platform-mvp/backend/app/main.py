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
    
    # Include routers (to be added as Phase 0 develops)
    # from .api import assessments, threats, evidence, auth
    # app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    # app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"])
    # app.include_router(threats.router, prefix="/api/v1/threats", tags=["threats"])
    # app.include_router(evidence.router, prefix="/api/v1/evidence", tags=["evidence"])
    
    return app


app = create_app()
