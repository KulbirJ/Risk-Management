#!/usr/bin/env python3
"""Check what tables exist in the database"""
import os
import sys
from pathlib import Path

# Set DATABASE_URL
os.environ["DATABASE_URL"] = "postgresql://complianceadmin:g%23K%2A%5E58%5D%26bRN%3Aqe@compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432/postgres"

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])

print("=== Checking database tables ===\n")

with engine.connect() as conn:
    # Check if alembic_version table exists
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    
    tables = [row[0] for row in result]
    print(f"Tables in database: {tables}\n")
    
    # Check alembic version
    if 'alembic_version' in tables:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.fetchone()
        if version:
            print(f"Current migration version: {version[0]}")
        else:
            print("No migration version found in alembic_version table")
    else:
        print("alembic_version table does not exist - no migrations have run")
    
    # Check if assessments table exists
    if 'assessments' in tables:
        print("\n✓ assessments table EXISTS")
        result = conn.execute(text("SELECT COUNT(*) FROM assessments"))
        count = result.fetchone()[0]
        print(f"  Number of records: {count}")
    else:
        print("\n✗ assessments table DOES NOT EXIST")
    
    # Check other expected tables
    expected_tables = ['tenants', 'users', 'threats', 'recommendations', 'threat_catalogue']
    print("\nOther expected tables:")
    for table in expected_tables:
        if table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"  ✓ {table} (records: {count})")
        else:
            print(f"  ✗ {table} (missing)")
