#!/usr/bin/env python3
"""Run migrations with detailed output"""
import os
import sys
from pathlib import Path
import logging

# Set up logging FIRST
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)

# Set DATABASE_URL
os.environ["DATABASE_URL"] = "postgresql://complianceadmin:g%23K%2A%5E58%5D%26bRN%3Aqe@compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432/postgres"

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

print("=" * 80)
print("RUNNING DATABASE MIGRATIONS")
print("=" * 80)

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

# Check database connection first
print("\n1. Testing database connection...")
try:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        pg_version = result.fetchone()[0]
        print(f"   ✓ Connected to PostgreSQL")
        print(f"   Version: {pg_version[:50]}...")
except Exception as e:
    print(f"   ✗ Failed to connect: {e}")
    sys.exit(1)

# Check alembic directory
print("\n2. Checking Alembic configuration...")
alembic_dir = backend_path / "app" / "db" / "alembic"
alembic_ini = alembic_dir / "alembic.ini"
versions_dir = alembic_dir / "versions"

print(f"   Alembic dir: {alembic_dir}")
print(f"   Exists: {alembic_dir.exists()}")
print(f"   Versions dir: {versions_dir}")
print(f"   Exists: {versions_dir.exists()}")

# List migration files
if versions_dir.exists():
    migration_files = list(versions_dir.glob("*.py"))
    migration_files = [f for f in migration_files if not f.name.startswith('__')]
    print(f"   Migration files found: {len(migration_files)}")
    for f in migration_files:
        print(f"     - {f.name}")

# Check current database state
print("\n3. Checking current database state...")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result]
    print(f"   Tables: {tables}")
    
    if 'alembic_version' in tables:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        if row:
            print(f"   Current version: {row[0]}")
        else:
            print(f"   Current version: (none - table is empty)")

# Create alembic config
print("\n4. Setting up Alembic configuration...")
cfg = Config(str(alembic_ini))
cfg.set_main_option('script_location', str(alembic_dir))
print(f"   Config created")
print(f"   Script location: {cfg.get_main_option('script_location')}")

# Check what Alembic thinks the current version is
print("\n5. Checking Alembic current version...")
try:
    from io import StringIO
    import contextlib
    
    # Capture output
    output = StringIO()
    with contextlib.redirect_stdout(output):
        command.current(cfg)
    
    current_output = output.getvalue()
    print(f"   Alembic current: {current_output if current_output.strip() else '(empty/no version)'}")
except Exception as e:
    print(f"   Error checking current: {e}")

# Check what Alembic thinks the head is
print("\n6. Checking Alembic head version...")
try:
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    print(f"   Head version: {head}")
    
    # Get all revisions
    revisions = list(script.walk_revisions())
    print(f"   Total revisions available: {len(revisions)}")
    for rev in revisions:
        print(f"     - {rev.revision}: {rev.doc}")
except Exception as e:
    print(f"   Error checking head: {e}")
    import traceback
    traceback.print_exc()

# Run migrations
print("\n7. Running migrations...")
print("-" * 80)
try:
    command.upgrade(cfg, 'head')
    print("-" * 80)
    print("   ✓ Migrations completed")
except Exception as e:
    print("-" * 80)
    print(f"   ✗ Error during migration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check final state
print("\n8. Checking final database state...")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result]
    print(f"   Tables now: {tables}")
    
    if 'alembic_version' in tables:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        if row:
            print(f"   Final version: {row[0]}")
    
    # Check for assessments table
    if 'assessments' in tables:
        print("\n   ✓✓✓ SUCCESS: assessments table exists!")
    else:
        print("\n   ✗✗✗ PROBLEM: assessments table still missing!")

print("\n" + "=" * 80)
print("MIGRATION PROCESS COMPLETE")
print("=" * 80)
