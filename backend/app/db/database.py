"""Database session and engine setup."""
import logging
from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from ..core.config import settings

logger = logging.getLogger(__name__)

# Determine database URL (from Secrets Manager if configured)
if settings.use_secrets_manager:
    try:
        from ..core.aws import get_db_url_from_secrets_manager
        database_url = get_db_url_from_secrets_manager(
            secret_name=settings.db_secret_name,
            region=settings.secrets_manager_region,
            db_name=settings.db_name
        )
        logger.info("Database URL loaded from AWS Secrets Manager")
    except Exception as e:
        logger.error(f"Failed to retrieve database URL from Secrets Manager: {e}")
        logger.warning("Falling back to DATABASE_URL environment variable")
        database_url = settings.database_url
else:
    database_url = settings.database_url
    logger.info(f"Using database URL from environment: {database_url.split('@')[0]}@{database_url.split('@')[1] if '@' in database_url else 'localhost'}")

# Create SQLAlchemy engine
engine: Engine = create_engine(
    database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,  # Verify connections before use
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


def get_db() -> Session:
    """FastAPI dependency: get database session for request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
