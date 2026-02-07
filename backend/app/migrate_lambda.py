"""
Lambda handler for running database migrations
This can be invoked manually or as part of deployment
"""
import os
import sys
from pathlib import Path

def lambda_handler(event, context):
    """
    Lambda handler that runs Alembic migrations
    Invoke with: aws lambda invoke --function-name compliance-platform-api --payload '{"action":"migrate"}' response.json
    """
    action = event.get("action", "")
    
    if action != "migrate" and action != "run_migrations":
        return {
            "statusCode": 400,
            "body": "Invalid action. Use action='migrate' or 'run_migrations'"
        }
    
    try:
        # Import here to avoid loading during normal API requests
        from alembic.config import Config
        from alembic import command
        
        # Get the alembic.ini path
        backend_path = Path("/var/task/app")  # Lambda deployment path
        alembic_ini_path = backend_path / "db" / "alembic" / "alembic.ini"
        
        if not alembic_ini_path.exists():
            return {
                "statusCode": 500,
                "body": f"Alembic config not found at {alembic_ini_path}"
            }
        
        # Create alembic config
        alembic_cfg = Config(str(alembic_ini_path))
        
        # Run migration
        command.upgrade(alembic_cfg, "head")
        
        # Get current version
        from io import StringIO
        import contextlib
        
        output = StringIO()
        with contextlib.redirect_stdout(output):
            command.current(alembic_cfg)
        
        current_version = output.getvalue()
        
        return {
            "statusCode": 200,
            "body": f"✅ Migrations completed successfully!\n\nCurrent version:\n{current_version}"
        }
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return {
            "statusCode": 500,
            "body": f"❌ Migration failed: {str(e)}\n\n{error_detail}"
        }

# For testing locally
if __name__ == "__main__":
    result = lambda_handler({"action": "migrate"}, {})
    print(result)
