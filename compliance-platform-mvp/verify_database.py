#!/usr/bin/env python3
"""
Verify database schema and tables exist
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Set DATABASE_URL if not set
if "DATABASE_URL" not in os.environ:
    print("Error: DATABASE_URL environment variable not set")
    sys.exit(1)

try:
    import psycopg2
    
    # Database connection parameters
    db_host = "compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com"
    db_port = 5432
    db_name = "postgres"
    db_user = "complianceadmin"
    db_password = "g#K*^58]&bRN:qe"
    
    print(f"Connecting to database: {db_host}:{db_port}/{db_name}")
    
    # Connect to database
    conn = psycopg2.connect(
        database=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )
    
    cursor = conn.cursor()
    
    # Check if alembic_version table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'alembic_version'
        );
    """)
    alembic_exists = cursor.fetchone()[0]
    
    if alembic_exists:
        cursor.execute("SELECT version_num FROM alembic_version;")
        version = cursor.fetchone()
        print(f"✅ Alembic version table exists. Current version: {version[0] if version else 'NONE'}")
    else:
        print("❌ Alembic version table does NOT exist - migrations have never run!")
    
    # List all tables
    cursor.execute("""
        SELECT tablename FROM pg_catalog.pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename;
    """)
    tables = cursor.fetchall()
    
    print(f"\nTables in database ({len(tables)}):")
    if tables:
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("  NO TABLES FOUND!")
    
    # Check for required tables
    required_tables = ['tenants', 'users', 'assessments', 'threats', 'controls', 'evidence']
    missing_tables = []
    
    table_names = [t[0] for t in tables]
    for req_table in required_tables:
        if req_table not in table_names:
            missing_tables.append(req_table)
    
    if missing_tables:
        print(f"\n❌ Missing required tables: {', '.join(missing_tables)}")
        print("\n⚠️  DATABASE SCHEMA IS INCOMPLETE - YOU NEED TO RUN MIGRATIONS!")
    else:
        print("\n✅ All required tables exist")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error connecting to database: {e}")
    sys.exit(1)
