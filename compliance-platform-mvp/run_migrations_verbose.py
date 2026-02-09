#!/usr/bin/env python3
"""
Run database migrations with verbose output
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
database_url = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
os.environ["DATABASE_URL"] = database_url

print(f"=" * 80)
print(f"RUNNING DATABASE MIGRATIONS")
print(f"=" * 80)
print(f"Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
print(f"User: {DB_USER}")
print()

try:
    from alembic.config import Config
    from alembic import command
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, text

    # Path to alembic.ini
    alembic_dir = backend_path / "app" / "db" / "alembic"
    alembic_ini_path = alembic_dir / "alembic.ini"
    versions_dir = alembic_dir / "versions"

    print(f"Alembic config: {alembic_ini_path}")
    print(f"Versions dir: {versions_dir}")
    
    if not alembic_ini_path.exists():
        print(f"❌ Error: alembic.ini not found at {alembic_ini_path}")
        sys.exit(1)

    # Check for migration files
    migration_files = list(versions_dir.glob("*.py"))
    migration_files = [f for f in migration_files if f.name != "__pycache__"]
    print(f"\nFound {len(migration_files)} migration file(s):")
    for f in migration_files:
        print(f"  - {f.name}")
    print()

    # Create alembic config
    alembic_cfg = Config(str(alembic_ini_path))
    
    # CRITICAL: Set script location to absolute path of the alembic directory
    # This ensures Alembic can find the versions/ subdirectory
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    
    # Also set the version_locations to absolute path
    alembic_cfg.set_main_option("version_locations", str(versions_dir))
    
    # Override sqlalchemy.url with environment variable
    # Escape % characters for ConfigParser by doubling them
    escaped_url = database_url.replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", escaped_url)

    # Check current database version before migration
    print("Checking current database state...")
    engine = create_engine(database_url)
    with engine.connect() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            )
        """))
        table_exists = result.scalar()
        
        if table_exists:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
            print(f"Current version: {current_version if current_version else 'NONE (table empty)'}")
        else:
            print("alembic_version table does not exist yet")
        conn.commit()
    
    print("\n" + "=" * 80)
    print("RUNNING ALEMBIC UPGRADE HEAD...")
    print("=" * 80)
    
    # Show what revisions will be applied
    script = ScriptDirectory.from_config(alembic_cfg)
    revisions = list(script.walk_revisions())
    print(f"\nAvailable revisions ({len(revisions)}):")
    for rev in revisions:
        print(f"  - {rev.revision}: {rev.doc}")
    
    # Run migrations with verbose output
    import logging
    logging.basicConfig()
    logging.getLogger('alembic').setLevel(logging.DEBUG)
    
    command.upgrade(alembic_cfg, "head", sql=False)
    
    print("\n" + "=" * 80)
    print("✅ MIGRATIONS COMPLETED!")
    print("=" * 80)
    
    # Show current version after migration
    print("\nCurrent database version after migration:")
    command.current(alembic_cfg, verbose=True)
    
    # Verify tables were created
    print("\n" + "=" * 80)
    print("VERIFYING TABLES...")
    print("=" * 80)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"\nTables in database ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")
        
        required_tables = ['tenants', 'users', 'assessments', 'threats', 'controls', 'evidence']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"\n❌ Missing required tables: {', '.join(missing_tables)}")
        else:
            print(f"\n✅ All required tables present!")
        conn.commit()

except Exception as e:
    print(f"\n❌ Error running migrations: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
