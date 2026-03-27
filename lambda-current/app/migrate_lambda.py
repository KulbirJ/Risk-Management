"""
Lambda handler for running database migrations and seeding
This can be invoked manually or as part of deployment
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID

def seed_database():
    """Seed database with test tenant and user."""
    from app.db.database import SessionLocal
    from app.models.models import Tenant, User
    
    db = SessionLocal()
    results = []
    
    try:
        tenant_id = UUID("67636bd3-9846-4bde-806f-aea369fc9457")
        user_id = UUID("0bc9d6a9-f342-452e-9297-ee33f44d4f84")
        
        # Check/create tenant
        existing_tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if existing_tenant:
            results.append(f"Tenant {tenant_id} already exists")
        else:
            tenant = Tenant(
                id=tenant_id,
                name="Test Organization",
                region="ca-west-1",
                settings={},
                created_at=datetime.utcnow()
            )
            db.add(tenant)
            results.append(f"Created tenant: {tenant_id}")
        
        # Check/create user
        existing_user = db.query(User).filter(User.id == user_id).first()
        if existing_user:
            results.append(f"User {user_id} already exists")
        else:
            user = User(
                id=user_id,
                tenant_id=tenant_id,
                email="test.user@example.com",
                display_name="Test User",
                cognito_sub=None,
                roles=["admin", "assessor"],
                is_active=True,
                created_at=datetime.utcnow(),
                last_login=None
            )
            db.add(user)
            results.append(f"Created user: {user_id}")
        
        db.commit()
        return True, results
        
    except Exception as e:
        db.rollback()
        return False, [str(e)]
    finally:
        db.close()

def lambda_handler(event, context):
    """
    Lambda handler that runs Alembic migrations or seeds data.
    Invoke with: 
      aws lambda invoke --function-name compliance-platform-api --payload '{"action":"migrate"}' response.json
      aws lambda invoke --function-name compliance-platform-api --payload '{"action":"seed"}' response.json
    """
    action = event.get("action", "")
    
    # Handle seed action
    if action == "seed":
        try:
            success, results = seed_database()
            return {
                "statusCode": 200 if success else 500,
                "body": "✅ Seed completed!\n" + "\n".join(results) if success else "❌ Seed failed: " + "\n".join(results)
            }
        except Exception as e:
            import traceback
            return {
                "statusCode": 500,
                "body": f"❌ Seed failed: {str(e)}\n\n{traceback.format_exc()}"
            }
    
    # Handle migrate action
    if action not in ("migrate", "run_migrations"):
        return {
            "statusCode": 400,
            "body": "Invalid action. Use action='migrate', 'run_migrations', or 'seed'"
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
