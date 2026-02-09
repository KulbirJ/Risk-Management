#!/usr/bin/env python3
"""Debug Alembic script discovery"""
import os
import sys
from pathlib import Path

# Set DATABASE_URL
os.environ["DATABASE_URL"] = "postgresql://complianceadmin:g%23K%2A%5E58%5D%26bRN%3Aqe@compliance-platform-db-dev.cbc4wfpgdhwx.ca-west-1.rds.amazonaws.com:5432/postgres"

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from alembic.config import Config
from alembic.script import ScriptDirectory

alembic_dir = backend_path / "app" / "db" / "alembic"
alembic_ini = alembic_dir / "alembic.ini"

print("Creating config...")
cfg = Config(str(alembic_ini))

# DON'T override script_location - let it use the relative path from the ini file
print(f"Script location from ini: {cfg.get_main_option('script_location')}")
print(f"Version locations from ini: {cfg.get_main_option('version_locations')}")

print("\nCreating ScriptDirectory...")
try:
    script = ScriptDirectory.from_config(cfg)
    print(f"  Script dir: {script.dir}")
    print(f"  Versions: {script.versions}")
    
    print("\nLooking for revisions...")
    revisions = list(script.walk_revisions())
    print(f"  Found: {len(revisions)}")
    
    for rev in revisions:
        print(f"    - {rev.revision}: {rev.doc}")
        print(f"      module: {rev.module}")
        
    head = script.get_current_head()
    print(f"\n  Head: {head}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Now try with absolute path
print("\n" + "="*80)
print("TRYING WITH ABSOLUTE SCRIPT_LOCATION")
print("="*80)

cfg2 = Config(str(alembic_ini))
cfg2.set_main_option('script_location', str(alembic_dir))
print(f"Script location set to: {cfg2.get_main_option('script_location')}")

print("\nCreating ScriptDirectory...")
try:
    script2 = ScriptDirectory.from_config(cfg2)
    print(f"  Script dir: {script2.dir}")
    print(f"  Versions: {script2.versions}")
    
    print("\nLooking for revisions...")
    revisions2 = list(script2.walk_revisions())
    print(f"  Found: {len(revisions2)}")
    
    for rev in revisions2:
        print(f"    - {rev.revision}: {rev.doc}")
        
    head2 = script2.get_current_head()
    print(f"\n  Head: {head2}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
