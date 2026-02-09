#!/usr/bin/env python3
"""
Run database migrations directly against RDS from local machine
This connects to RDS and runs Alembic migrations
"""
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Database connection details
DB_HOST = "compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "complianceadmin"
DB_PASSWORD = "g#K*^58]&bRN:qe"

# Build DATABASE_URL with URL-encoded password
encoded_password = quote_plus(DB_PASSWORD)
os.environ["DATABASE_URL"] = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"Running migrations...")
print(f"Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")

try:
    from alembic.config import Config
    from alembic import command

    # Path to alembic.ini
    alembic_ini_path = backend_path / "app" / "db" / "alembic" / "alembic.ini"

    if not alembic_ini_path.exists():
        print(f"Error: alembic.ini not found at {alembic_ini_path}")
        sys.exit(1)

    print(f"Using config: {alembic_ini_path}")

    # Create alembic config
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(alembic_ini_path.parent))

    # Override sqlalchemy.url with environment variable
    # Use %% to escape % characters for ConfigParser
    escaped_url = os.environ["DATABASE_URL"].replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", escaped_url)

    # Run migrations
    print("\nRunning alembic upgrade head...")
    command.upgrade(alembic_cfg, "head")
    
    print("\n✅ Migrations completed successfully!")
    
    # Show current version
    print("\nCurrent database version:")
    command.current(alembic_cfg)

except Exception as e:
    print(f"\n❌ Error running migrations: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
