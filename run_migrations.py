#!/usr/bin/env python
"""Run Alembic migrations"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from alembic.config import Config
from alembic import command

def run_migrations():
    """Run database migrations"""
    try:
        # Get alembic config
        alembic_ini = backend_path / "app" / "db" / "alembic" / "alembic.ini"
        
        if not alembic_ini.exists():
            print(f"Error: alembic.ini not found at {alembic_ini}")
            return False
        
        print(f"Using alembic.ini: {alembic_ini}")
        print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')}")
        
        # Create config
        alembic_cfg = Config(str(alembic_ini))
        
        # Run upgrade
        print("Running migrations...")
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully!")
        
        # Show current version
        print("\nCurrent database version:")
        command.current(alembic_cfg)
        
        return True
        
    except Exception as e:
        print(f"Error running migrations: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
