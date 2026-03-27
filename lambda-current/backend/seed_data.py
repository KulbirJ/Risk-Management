#!/usr/bin/env python
"""Seed database with test tenant and user for local development."""
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.db.database import SessionLocal
from app.models.models import Tenant, User
from datetime import datetime


def seed_database():
    """Seed database with test data."""
    db = SessionLocal()
    
    try:
        # Test tenant ID (from docker-compose environment variables)
        tenant_id = UUID("67636bd3-9846-4bde-806f-aea369fc9457")
        user_id = UUID("0bc9d6a9-f342-452e-9297-ee33f44d4f84")
        
        # Check if tenant already exists
        existing_tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if existing_tenant:
            print(f"Tenant {tenant_id} already exists")
        else:
            # Create test tenant
            tenant = Tenant(
                id=tenant_id,
                name="Test Organization",
                region="ca-west-1",
                settings={},
                created_at=datetime.utcnow()
            )
            db.add(tenant)
            print(f"Created tenant: {tenant_id}")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.id == user_id).first()
        if existing_user:
            print(f"User {user_id} already exists")
        else:
            # Create test user
            user = User(
                id=user_id,
                tenant_id=tenant_id,
                email="test.user@example.com",
                display_name="Test User",
                cognito_sub=None,  # Mock auth mode
                roles=["admin", "assessor"],
                is_active=True,
                created_at=datetime.utcnow(),
                last_login=None
            )
            db.add(user)
            print(f"Created user: {user_id}")
        
        db.commit()
        print("\n✅ Database seeded successfully!")
        print(f"   Tenant ID: {tenant_id}")
        print(f"   User ID: {user_id}")
        print(f"   Email: test.user@example.com")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()
    
    return True


if __name__ == "__main__":
    success = seed_database()
    sys.exit(0 if success else 1)
