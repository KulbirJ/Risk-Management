# AWS Phase 1 - Manual Setup Guide via AWS Console

## Prerequisites
- AWS Account with admin access
- Region: ca-west-1 (Canada West - Calgary)

---

## Step-by-Step Manual Setup

### 1. Create RDS PostgreSQL Instance

1. Go to: **RDS Console** → https://ca-west-1.console.aws.amazon.com/rds
2. Click **"Create database"**
3. Configuration:
   - **Engine**: PostgreSQL 15.5
   - **Templates**: Free tier (or Dev/Test)
   - **DB instance identifier**: `compliance-platform-db-dev`
   - **Master username**: `complianceadmin`
   - **Master password**: [Create secure password - save it!]
   - **DB instance class**: db.t4g.micro
   - **Storage**: 20 GB gp3
   - **VPC**: Default VPC
   - **Public access**: No
   - **VPC security group**: Create new → `compliance-platform-rds-sg-dev`
     - Add inbound rule: PostgreSQL (5432) from 0.0.0.0/0 (or your VPC CIDR)
   - **Backup retention**: 7 days
4. Click **"Create database"** (takes 5-10 minutes)
5. **Save the endpoint** once available (e.g., `*.ca-west-1.rds.amazonaws.com`)

---

### 2. Create ElastiCache Redis Cluster

1. Go to: **ElastiCache Console** → https://ca-west-1.console.aws.amazon.com/elasticache
2. Click **"Create cluster"** → **Redis**
3. Configuration:
   - **Cluster mode**: Disabled
   - **Name**: `compliance-platform-cache-dev`
   - **Engine version**: 7.x
   - **Node type**: cache.t4g.micro
   - **Number of replicas**: 0
   - **Subnet group**: Create new → `compliance-platform-cache-subnet-group`
     - Add all subnets from default VPC
   - **Security group**: Create new → `compliance-platform-cache-sg-dev`
     - Add inbound rule: Custom TCP (6379) from 0.0.0.0/0 (or your VPC CIDR)
4. Click **"Create"** (takes 5-10 minutes)
5. **Save the endpoint** once available (e.g., `*.cache.amazonaws.com`)

---

### 3. Create S3 Bucket

1. Go to: **S3 Console** → https://s3.console.aws.amazon.com/s3
2. Click **"Create bucket"**
3. Configuration:
   - **Bucket name**: `compliance-platform-evidence-dev` (must be globally unique)
   - **Region**: ca-west-1
   - **Block all public access**: Checked
   - **Versioning**: Enable
   - **Encryption**: Enable (SSE-S3)
4. Click **"Create bucket"**
5. After creation, go to **Management** tab:
   - Create lifecycle rule:
     - **Rule name**: DeleteOldEvidenceFiles
     - **Prefix**: evidence/
     - **Expiration**: 365 days
     - **Status**: Enabled

---

### 4. Create IAM Role for Lambda

1. Go to: **IAM Console** → https://console.aws.amazon.com/iam
2. Click **"Roles"** → **"Create role"**
3. Configuration:
   - **Trusted entity**: AWS service
   - **Use case**: Lambda
   - Click **"Next"**
4. Attach policies:
   - ☑ `AWSLambdaBasicExecutionRole`
   - ☑ `AmazonS3FullAccess`
   - ☑ `SecretsManagerReadWrite`
5. **Role name**: `compliance-platform-lambda-role`
6. Click **"Create role"**
7. **Copy the Role ARN** (e.g., `arn:aws:iam::031195399879:role/compliance-platform-lambda-role`)

---

### 5. Create Lambda Function

1. Go to: **Lambda Console** → https://ca-west-1.console.aws.amazon.com/lambda
2. Click **"Create function"**
3. Configuration:
   - **Function name**: `compliance-platform-api`
   - **Runtime**: Python 3.11
   - **Execution role**: Use existing role → `compliance-platform-lambda-role`
4. Click **"Create function"**
5. **Configuration** tab:
   - **Memory**: 512 MB
   - **Timeout**: 30 seconds
   - **Environment variables**:
     ```
     DATABASE_URL = postgresql://complianceadmin:YOUR_PASSWORD@RDS_ENDPOINT:5432/postgres
     REDIS_URL = redis://CACHE_ENDPOINT:6379/0
     AWS_REGION_NAME = ca-west-1
     S3_BUCKET_NAME = compliance-platform-evidence-dev
     ENVIRONMENT = dev
     ```
6. Deploy placeholder code (will be replaced by CI/CD):
   ```python
   def lambda_handler(event, context):
       return {
           'statusCode': 200,
           'body': 'Placeholder - Deploy via CI/CD'
       }
   ```

---

### 6. Create API Gateway HTTP API

1. Go to: **API Gateway Console** → https://ca-west-1.console.aws.amazon.com/apigateway
2. Click **"Create API"** → **"HTTP API"** → **"Build"**
3. Configuration:
   - **API name**: `compliance-platform-api-gateway`
   - **Integration**: Lambda
   - **Lambda function**: `compliance-platform-api`
   - **API Gateway version**: 2.0
4. Click **"Next"** → **"Next"** → **"Create"**
5. Go to **"Authorization"** → Configure CORS:
   - **Allowed origins**: `*` (or your frontend domain)
   - **Allowed methods**: All
   - **Allowed headers**: All
6. **Copy the Invoke URL** (e.g., `https://abc123.execute-api.ca-west-1.amazonaws.com`)

---

### 7. Create Secrets Manager Secret

1. Go to: **Secrets Manager** → https://ca-west-1.console.aws.amazon.com/secretsmanager
2. Click **"Store a new secret"**
3. Configuration:
   - **Secret type**: Other type of secret
   - **Key/value pairs**:
     ```json
     {
       "username": "complianceadmin",
       "password": "YOUR_RDS_PASSWORD",
       "host": "YOUR_RDS_ENDPOINT",
       "port": 5432,
       "dbname": "postgres",
       "url": "postgresql://complianceadmin:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres"
     }
     ```
   - **Secret name**: `compliance-platform/dev/database`
4. Click **"Next"** → **"Next"** → **"Store"**

---

### 8. Setup AWS Amplify for Frontend

1. Go to: **Amplify Console** → https://console.aws.amazon.com/amplify
2. Click **"New app"** → **"Host web app"**
3. Connect to GitHub:
   - Authorize AWS Amplify
   - **Repository**: `KulbirJ/Risk-Management`
   - **Branch**: `main`
4. Build settings (auto-detected from `amplify.yml`):
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: .next
       files:
         - '**/*'
   ```
5. **Environment variables**:
   ```
   NEXT_PUBLIC_API_URL = https://YOUR_API_GATEWAY_URL
   NEXT_PUBLIC_AWS_REGION = ca-west-1
   ```
6. Click **"Save and deploy"**
7. **Copy the Amplify URL** (e.g., `https://main.abc123.amplifyapp.com`)

---

## Summary of Resources Created

| Resource | Name/ID | Purpose | Cost/Month |
|----------|---------|---------|------------|
| RDS | compliance-platform-db-dev | PostgreSQL database | $12-15 |
| ElastiCache | compliance-platform-cache-dev | Redis cache | $8-10 |
| S3 | compliance-platform-evidence-dev | File storage | $1-3 |
| Lambda | compliance-platform-api | Backend API | $2-5 |
| API Gateway | compliance-platform-api-gateway | HTTP endpoint | $1-2 |
| Amplify | [auto-generated] | Frontend hosting | $1-5 |
| IAM Role | compliance-platform-lambda-role | Lambda permissions | Free |
| Secrets Manager | compliance-platform/dev/database | DB credentials | $0.40 |
| **TOTAL** | | | **$25-40** |

---

## Configuration for Local Development

Update your local `.env` or `docker-compose.yaml`:

```env
DATABASE_URL=postgresql://complianceadmin:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres
REDIS_URL=redis://YOUR_CACHE_ENDPOINT:6379/0
AWS_REGION_NAME=ca-west-1
S3_BUCKET_NAME=compliance-platform-evidence-dev
NEXT_PUBLIC_API_URL=https://YOUR_API_GATEWAY_URL
```

---

## GitHub Secrets for CI/CD

Add to: `https://github.com/KulbirJ/Risk-Management/settings/secrets/actions`

```
AWS_ACCESS_KEY_ID = [Your AWS Access Key]
AWS_SECRET_ACCESS_KEY = [Your AWS Secret Key]
AWS_ACCOUNT_ID = 031195399879
```

**To create access keys:**
1. IAM Console → Users → Your user
2. Security credentials tab
3. Create access key → CLI
4. Save the credentials securely

---

## Testing Your Setup

### Test Lambda Function:
```bash
curl https://YOUR_API_GATEWAY_URL/health
```

### Test Frontend:
Open browser: `https://YOUR_AMPLIFY_URL`

### Test Database Connection:
```bash
psql -h YOUR_RDS_ENDPOINT -U complianceadmin -d postgres
```

---

## Next Steps

1. ✅ All AWS resources created
2. ⏭️ Configure GitHub secrets
3. ⏭️ Update local environment variables
4. ⏭️ Push code to trigger CI/CD deployment
5. ⏭️ Run database migrations
6. ⏭️ Test application

---

## Troubleshooting

**Can't connect to RDS:**
- Check security group allows your IP
- Verify endpoint is correct
- Ensure password is correct

**Lambda errors:**
- Check CloudWatch Logs
- Verify environment variables
- Check IAM role permissions

**API Gateway 502:**
- Check Lambda function logs
- Verify Lambda integration
- Test Lambda directly first

---

## Cost Monitoring

Set up billing alert:
1. CloudWatch → Billing → Create alarm
2. Threshold: $50 USD
3. Email notification when exceeded

---

## Cleanup (To Stop Charges)

When you want to delete everything:
1. Lambda → Delete function
2. API Gateway → Delete API
3. RDS → Delete database (skip final snapshot for dev)
4. ElastiCache → Delete cluster
5. S3 → Empty bucket → Delete bucket
6. Amplify → Delete app
7. IAM → Delete role

**Estimated time to clean up**: 10-15 minutes
