"""
Run database migrations against AWS RDS
"""
import os
import sys
from pathlib import Path

# Set environment variable for RDS database
os.environ["DATABASE_URL"] = "postgresql://complianceadmin:g#K*^58]&bRN:qe@compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432/postgres"

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Now import and run alembic
from alembic.config import Config
from alembic import command

# Path to alembic.ini
alembic_ini_path = backend_path / "backend" / "app" / "db" / "alembic" / "alembic.ini"

print(f"Running migrations with config: {alembic_ini_path}")
print(f"Database URL: {os.environ['DATABASE_URL'][:60]}...")

# Create alembic config
alembic_cfg = Config(str(alembic_ini_path))

# Run migration
try:
    print("\nUpgrading database to head...")
    command.upgrade(alembic_cfg, "head")
    print("\n✅ Migration completed successfully!")
    
    print("\nCurrent database version:")
    command.current(alembic_cfg)
    
except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    sys.exit(1)
