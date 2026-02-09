#!/usr/bin/env python3
"""Test migration script"""
import os
import sys
from pathlib import Path

# Set DATABASE_URL
os.environ["DATABASE_URL"] = "postgresql://complianceadmin:g%23K%2A%5E58%5D%26bRN%3Aqe@compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432/postgres"

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from alembic.config import Config
from alembic import command
import logging

# Enable INFO logging to see Alembic messages
logging.basicConfig()
logging.getLogger('alembic').setLevel(logging.INFO)

# Path to alembic directory
alembic_dir = backend_path / "app" / "db" / "alembic"
alembic_ini = alembic_dir / "alembic.ini"

print(f"Alembic dir: {alembic_dir}")
print(f"Alembic ini: {alembic_ini}")
print(f"Alembic dir exists: {alembic_dir.exists()}")
print(f"Alembic ini exists: {alembic_ini.exists()}")

# Create config
cfg = Config(str(alembic_ini))
cfg.set_main_option('script_location', str(alembic_dir))

print("\n=== Current database version ===")
command.current(cfg)

print("\n=== Running migrations ===")
command.upgrade(cfg, 'head')

print("\n=== New database version ===")
command.current(cfg)

print("\nMigrations completed!")
