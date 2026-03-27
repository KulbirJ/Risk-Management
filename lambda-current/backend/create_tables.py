#!/usr/bin/env python
"""Create database tables directly from SQLAlchemy models"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.db.database import Base, engine, SessionLocal
from app.models.models import (
    Tenant, User, Assessment, Threat, Evidence,
    Recommendation, ActiveRisk, AuditLog, ThreatCatalogue
)

def create_tables():
    """Create all database tables"""
    try:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        # List tables
        print("\nVerifying tables in database...")
        with SessionLocal() as session:
            result = session.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
            tables = result.fetchall()
            print(f"Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
        
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)
