# AWS Database & Secrets Manager Setup - Phase 0

## Your AWS Configuration

- **AWS Account ID**: 031195399879
- **Region**: ca-central-1 (Canada)
- **Database Name**: multitenantpostgresdb
- **Credentials Storage**: AWS Secrets Manager

## Database Configuration

### Aurora Serverless v2 (RDS) — multitenantpostgresdb

Your database is already configured in AWS. The application connects to it in two ways:

#### Option 1: Local Development (Direct Connection)

For local development with Docker, use direct PostgreSQL connection string:

```env
DATABASE_URL=postgresql://admin:password@localhost:5432/multitenantpostgresdb
USE_SECRETS_MANAGER=False
```

Docker Compose runs a local Postgres container that mimics your AWS database.

#### Option 2: AWS Deployment (Secrets Manager)

When deployed to AWS, fetch credentials from Secrets Manager:

```env
USE_SECRETS_MANAGER=True
SECRETS_MANAGER_REGION=ca-central-1
DB_SECRET_NAME=compliance-platform/db/credentials
DB_NAME=multitenantpostgresdb
```

## AWS Secrets Manager Setup (Already Done)

Your secret is stored in AWS Secrets Manager:

**Secret Name**: `compliance-platform/db/credentials`  
**ARN**: `arn:aws:secretsmanager:ca-central-1:031195399879:secret:compliance-platform/db/credentials`  
**Region**: ca-central-1  
**Format**: JSON

### Expected Secret Content

The secret should contain JSON with the following structure:

```json
{
  "host": "your-rds-endpoint.ca-central-1.rds.amazonaws.com",
  "port": 5432,
  "username": "postgres_user",
  "password": "secure_password_here",
  "engine": "postgres"
}
```

To verify or update your secret in AWS Console:

1. Go to AWS Secrets Manager
2. Search for `compliance-platform/db/credentials`
3. Click "Retrieve secret value" to view current credentials
4. Click "Edit secret" to update if needed

## Code Implementation

### Local Development (Phase 0)

```python
# In .env
DATABASE_URL=postgresql://admin:password@localhost:5432/multitenantpostgresdb
USE_SECRETS_MANAGER=False

# In docker-compose.yaml
postgres:
  environment:
    POSTGRES_USER: admin
    POSTGRES_PASSWORD: password
    POSTGRES_DB: multitenantpostgresdb
```

### AWS Deployment (Phase 1)

The application automatically fetches credentials from Secrets Manager when `USE_SECRETS_MANAGER=True`:

```python
# backend/app/core/aws.py — get_db_url_from_secrets_manager()
def get_db_url_from_secrets_manager(secret_name, region, db_name):
    """
    Fetches credentials from AWS Secrets Manager and builds PostgreSQL URL.
    Example: postgresql://user:pass@host:5432/multitenantpostgresdb
    """
    client = SecretsManagerClient(region=region)
    secret_dict = client.get_secret(secret_name)
    
    host = secret_dict.get("host")
    port = secret_dict.get("port", 5432)
    username = secret_dict.get("username")
    password = secret_dict.get("password")
    
    return f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
```

### Database Connection Flow

```
1. Application starts (backend/app/main.py)
   ↓
2. Load config from environment (backend/app/core/config.py)
   ↓
3. Check if USE_SECRETS_MANAGER=True
   ├─ YES → Fetch credentials from AWS Secrets Manager → Build URL
   └─ NO  → Use DATABASE_URL from environment
   ↓
4. Connect to PostgreSQL using constructed URL
   ↓
5. Run Alembic migrations
```

## Setting Up Secrets Manager Secret (If Not Already Done)

### Via AWS CLI

```bash
# Create secret with credentials
aws secretsmanager create-secret \
  --name compliance-platform/db/credentials \
  --secret-string '{
    "host": "multitenantpostgresdb.ca-central-1.rds.amazonaws.com",
    "port": 5432,
    "username": "admin",
    "password": "your_secure_password",
    "engine": "postgres"
  }' \
  --region ca-central-1
```

### Via AWS Console

1. Go to AWS Secrets Manager
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Paste the JSON above
5. Name it: `compliance-platform/db/credentials`
6. Add tags: `Project: CompliancePlatform`, `Phase: Phase0`
7. Click "Store secret"

## IAM Permissions Required

For the application to access Secrets Manager, ensure the ECS task role has this permission:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ca-central-1:031195399879:secret:compliance-platform/db/credentials*"
      ]
    }
  ]
}
```

## Local Development Quick Start

### Step 1: Clone and Setup

```bash
cd c:\Users\user1-baseNaultha\Threat Risk Assessment\compliance-platform-mvp
cp .env.example .env
```

### Step 2: Verify .env has correct database name

```env
DATABASE_URL=postgresql://admin:password@localhost:5432/multitenantpostgresdb
DB_NAME=multitenantpostgresdb
USE_SECRETS_MANAGER=False
```

### Step 3: Start Docker Compose

```bash
docker-compose up -d
```

### Step 4: Run Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### Step 5: Verify Database Connection

```bash
# Check health
curl http://localhost:8000/health

# Check database tables
docker-compose exec postgres psql -U admin -d multitenantpostgresdb -c "\dt"
```

## Troubleshooting

### "database does not exist" error

**Cause**: Docker container using wrong database name

**Fix**: 
```bash
# Ensure docker-compose.yaml has:
POSTGRES_DB: multitenantpostgresdb

# Rebuild containers
docker-compose down
docker-compose up -d
```

### "connection refused" error

**Cause**: Postgres not running or not ready

**Fix**:
```bash
docker-compose logs postgres
docker-compose restart postgres
```

### Secrets Manager connection error (when testing AWS)

**Cause**: IAM role doesn't have permission or secret doesn't exist

**Fix**:
```bash
# Verify secret exists
aws secretsmanager describe-secret \
  --secret-id compliance-platform/db/credentials \
  --region ca-central-1

# Check IAM permissions on ECS task role
```

## Migration: Local → AWS (Future)

When deploying to AWS ECS:

1. Update environment variables:
   ```env
   USE_SECRETS_MANAGER=True
   DB_SECRET_NAME=compliance-platform/db/credentials
   SECRETS_MANAGER_REGION=ca-central-1
   DB_NAME=multitenantpostgresdb
   ```

2. Ensure ECS task role has Secrets Manager permissions (listed above)

3. Deploy application

4. Application will automatically fetch credentials and connect to multitenantpostgresdb

## Phase 1: Connection Pooling (Future)

For high concurrency deployments, consider using RDS Proxy:

```
Application → RDS Proxy → Aurora Cluster (multitenantpostgresdb)
```

RDS Proxy will require separate IAM role and configuration.

## References

- AWS Secrets Manager: https://docs.aws.amazon.com/secretsmanager/
- PostgreSQL Connection Strings: https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
- SQLAlchemy Connection Strings: https://docs.sqlalchemy.org/core/engines.html#postgresql
- Alembic Migrations: https://alembic.sqlalchemy.org/
