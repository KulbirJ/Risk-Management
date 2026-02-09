"""Alembic environment configuration."""
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import Base for autogenerate
import sys
# Add backend directory to path (go up 3 levels from alembic dir to backend)
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, backend_path)

from app.db.database import Base
from app.models.models import (
    Tenant, User, Assessment, Threat, Evidence,
    Recommendation, ActiveRisk, AuditLog, ThreatCatalogue
)

# Alembic Config object
config = context.config

# Interpret the config file for logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Override sqlalchemy.url with DATABASE_URL environment variable if present
    configuration = config.get_section(config.config_ini_section, {})
    if 'sqlalchemy.url' not in configuration or configuration['sqlalchemy.url'] == 'driver://user:pass@localhost/dbname':
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            configuration['sqlalchemy.url'] = database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
