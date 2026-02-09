#!/usr/bin/env python3
"""
Seed test tenant and user for testing the API
"""
import psycopg2
from datetime import datetime
from uuid import UUID

# Database connection details
DB_HOST = "compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "complianceadmin"
DB_PASSWORD = "g#K*^58]&bRN:qe"

# Test data IDs (matching the headers used in API calls)
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
USER_ID = "550e8400-e29b-41d4-a716-446655440001"

print(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")

try:
    # Connect to database
    conn = psycopg2.connect(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    
    cursor = conn.cursor()
    
    # Check if tenant already exists
    cursor.execute("SELECT id FROM tenants WHERE id = %s", (TENANT_ID,))
    tenant_exists = cursor.fetchone()
    
    if not tenant_exists:
        print(f"\nCreating test tenant: {TENANT_ID}")
        cursor.execute("""
            INSERT INTO tenants (id, name, region, settings, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            TENANT_ID,
            "Test Tenant",
            "ca-west-1",
            '{}',
            datetime.utcnow()
        ))
        print("✅ Tenant created")
    else:
        print(f"✅ Tenant already exists: {TENANT_ID}")
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE id = %s", (USER_ID,))
    user_exists = cursor.fetchone()
    
    if not user_exists:
        print(f"\nCreating test user: {USER_ID}")
        cursor.execute("""
            INSERT INTO users (id, tenant_id, email, display_name, roles, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            USER_ID,
            TENANT_ID,
            "test@example.com",
            "Test User",
            '["admin"]',
            True,
            datetime.utcnow()
        ))
        print("✅ User created")
    else:
        print(f"✅ User already exists: {USER_ID}")
    
    # Commit changes
    conn.commit()
    
    print("\n" + "="*60)
    print("✅ Test data seeded successfully!")
    print("="*60)
    print(f"\nTenant ID: {TENANT_ID}")
    print(f"User ID:   {USER_ID}")
    print(f"Email:     test@example.com")
    print("\nYou can now use these IDs in your API requests:")
    print(f'  x-tenant-id: {TENANT_ID}')
    print(f'  x-user-id: {USER_ID}')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error seeding data: {e}")
    import traceback
    traceback.print_exc()
