# AWS Phase 1 Serverless Architecture - Resource Requirements

## Overview
Phase 1 implements a cost-optimized serverless architecture for development/testing.
**Estimated Monthly Cost: $25-40**

---

## Required AWS Resources

### 1. **RDS PostgreSQL Instance**
- **Purpose**: Primary database for multi-tenant data
- **Instance Type**: `db.t4g.micro`
- **Specifications**:
  - vCPUs: 2
  - Memory: 1 GB RAM
  - Storage: 20 GB gp3 (expandable)
  - Engine: PostgreSQL 15.5
  - Backup Retention: 7 days
  - Multi-AZ: No (single instance)
- **Cost**: ~$12-15/month
- **Provisioning**: Created by setup script
- **Connection**: Private (within VPC)

### 2. **ElastiCache Redis Cluster**
- **Purpose**: Session storage, rate limiting, caching
- **Node Type**: `cache.t4g.micro`
- **Specifications**:
  - vCPUs: 2
  - Memory: 555 MB
  - Engine: Redis 7.x
  - Nodes: 1 (non-clustered)
  - Replication: No (single node)
- **Cost**: ~$8-10/month
- **Provisioning**: Created by setup script
- **Connection**: Private (within VPC)

### 3. **AWS Lambda Function**
- **Purpose**: FastAPI backend API handler
- **Runtime**: Python 3.11
- **Specifications**:
  - Memory: 512 MB
  - Timeout: 30 seconds
  - Concurrency: 10 (reserved)
  - Handler: `app.main.lambda_handler`
  - Deployment: ZIP file (via CI/CD)
- **Cost**: ~$2-5/month (10K-50K requests)
  - First 1M requests/month free
  - $0.20 per 1M requests after
  - $0.0000166667 per GB-second
- **Provisioning**: Created by setup script, updated by CI/CD

### 4. **API Gateway HTTP API**
- **Purpose**: HTTP endpoint for Lambda function
- **Type**: HTTP API (cheaper than REST API)
- **Specifications**:
  - Protocol: HTTP
  - Integration: Lambda proxy
  - CORS: Enabled
  - Stage: $default (auto-deploy)
- **Cost**: ~$1-2/month
  - First 1M API calls/month free
  - $1.00 per million after
- **Provisioning**: Created by setup script
- **Endpoint Format**: `https://{api-id}.execute-api.ca-west-1.amazonaws.com`

### 5. **S3 Bucket**
- **Purpose**: Evidence file storage
- **Specifications**:
  - Versioning: Enabled
  - Encryption: AES-256 (SSE-S3)
  - Lifecycle: 365-day retention for evidence/
  - Access: Private (authenticated only)
  - Max file size: 500 MB
- **Cost**: ~$1-3/month
  - $0.023 per GB/month storage
  - $0.09 per GB transfer out
  - Assuming 50-100 GB storage
- **Provisioning**: Created by setup script

### 6. **AWS Amplify Hosting**
- **Purpose**: Next.js frontend hosting and CDN
- **Specifications**:
  - Build: Node.js 18
  - Deploy: Git-based (GitHub integration)
  - SSR: Supported (Next.js 14)
  - Custom domain: Optional
  - SSL: Free AWS certificate
- **Cost**: ~$1-5/month
  - Build minutes: 1,000 free/month
  - Hosting: First 15 GB served free
  - $0.023 per GB after
- **Provisioning**: Manual (via AWS Console)
- **Setup Steps**:
  1. AWS Console → Amplify → New App
  2. Connect GitHub repository
  3. Branch: main
  4. Build settings: Auto-detected (amplify.yml)
  5. Deploy

### 7. **VPC and Networking**
- **Purpose**: Network isolation for RDS and ElastiCache
- **Resources**:
  - Default VPC (free)
  - 2+ subnets across availability zones
  - Security groups for RDS (port 5432) and Redis (port 6379)
  - DB subnet group
  - Cache subnet group
- **Cost**: Free (using default VPC)
- **Provisioning**: Created by setup script

### 8. **IAM Roles and Policies**
- **Lambda Execution Role**:
  - `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
  - `AmazonS3FullAccess` (S3 operations)
  - `SecretsManagerReadWrite` (credentials access)
- **Cost**: Free
- **Provisioning**: Created by setup script

### 9. **AWS Secrets Manager**
- **Purpose**: Store database credentials securely
- **Secrets**:
  - `compliance-platform/dev/database` (RDS credentials)
- **Cost**: ~$0.40/month per secret
- **Provisioning**: Created by setup script
- **Rotation**: Manual (Phase 1)

---

## Total Estimated Monthly Cost Breakdown

| Service | Configuration | Est. Monthly Cost |
|---------|--------------|-------------------|
| RDS PostgreSQL | db.t4g.micro, 20GB gp3 | $12-15 |
| ElastiCache Redis | cache.t4g.micro, 1 node | $8-10 |
| Lambda | 512MB, 10K-50K requests | $2-5 |
| API Gateway | HTTP API, 10K-50K calls | $1-2 |
| S3 | 50-100GB storage + transfers | $1-3 |
| Amplify | Hosting + builds | $1-5 |
| Secrets Manager | 1 secret | $0.40 |
| **TOTAL** | | **$25.40 - $40.40** |

---

## Prerequisites for CI/CD Deployment

### GitHub Secrets (Required)
Add these secrets to your GitHub repository:

```
AWS_ACCESS_KEY_ID          - Your AWS access key
AWS_SECRET_ACCESS_KEY      - Your AWS secret key  
AWS_ACCOUNT_ID             - 031195399879
```

**To add secrets:**
1. GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret

### Local Environment Variables
Update `.env` files after infrastructure is created:

**Backend (.env or docker-compose.yaml):**
```bash
DATABASE_URL=postgresql://complianceadmin:PASSWORD@RDS_ENDPOINT:5432/postgres
REDIS_URL=redis://CACHE_ENDPOINT:6379/0
AWS_REGION_NAME=ca-west-1
S3_BUCKET_NAME=compliance-platform-evidence-dev
ENVIRONMENT=dev
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=https://API_GATEWAY_ENDPOINT
NEXT_PUBLIC_AWS_REGION=ca-west-1
```

---

## Provisioning Instructions

### Option 1: Automated Setup (Recommended)

**Using PowerShell (Windows):**
```powershell
cd scripts
.\setup-aws-infrastructure-lambda.ps1 -Environment dev -Region ca-west-1
```

**Using Bash (Linux/Mac):**
```bash
cd scripts
chmod +x setup-aws-infrastructure-lambda.sh
./setup-aws-infrastructure-lambda.sh dev ca-west-1
```

The script will:
- Create all AWS resources
- Configure security groups
- Set up networking
- Wait for resources to be ready
- Output connection strings and endpoints
- Display estimated costs

**Estimated Setup Time**: 10-15 minutes (mostly waiting for RDS/ElastiCache)

### Option 2: Manual Setup

If you prefer manual setup, follow these steps:

#### 1. Create VPC Resources
```bash
# Get default VPC ID
aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --region ca-west-1

# Create security groups
aws ec2 create-security-group \
  --group-name compliance-platform-rds-sg-dev \
  --description "RDS PostgreSQL security group" \
  --vpc-id vpc-xxxxx \
  --region ca-west-1
```

#### 2. Create RDS Instance
```bash
aws rds create-db-instance \
  --db-instance-identifier compliance-platform-db-dev \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version 15.5 \
  --master-username complianceadmin \
  --master-user-password YOUR_SECURE_PASSWORD \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name your-subnet-group \
  --backup-retention-period 7 \
  --no-publicly-accessible \
  --region ca-west-1
```

#### 3. Create ElastiCache Cluster
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id compliance-platform-cache-dev \
  --cache-node-type cache.t4g.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --cache-subnet-group-name your-cache-subnet-group \
  --security-group-ids sg-xxxxx \
  --region ca-west-1
```

#### 4. Create S3 Bucket
```bash
aws s3 mb s3://compliance-platform-evidence-dev --region ca-west-1
aws s3api put-bucket-versioning \
  --bucket compliance-platform-evidence-dev \
  --versioning-configuration Status=Enabled \
  --region ca-west-1
```

#### 5. Create Lambda Function
```bash
# Create IAM role first
aws iam create-role \
  --role-name compliance-platform-lambda-role \
  --assume-role-policy-document file://lambda-trust-policy.json

# Create Lambda function
aws lambda create-function \
  --function-name compliance-platform-api \
  --runtime python3.11 \
  --role arn:aws:iam::031195399879:role/compliance-platform-lambda-role \
  --handler app.main.lambda_handler \
  --zip-file fileb://placeholder.zip \
  --timeout 30 \
  --memory-size 512 \
  --region ca-west-1
```

#### 6. Create API Gateway
```bash
aws apigatewayv2 create-api \
  --name compliance-platform-api-gateway \
  --protocol-type HTTP \
  --target arn:aws:lambda:ca-west-1:031195399879:function:compliance-platform-api \
  --region ca-west-1
```

#### 7. Setup Amplify (AWS Console)
1. Go to AWS Amplify Console
2. Click "New app" → "Host web app"
3. Choose GitHub as source
4. Authorize and select repository: `KulbirJ/Risk-Management`
5. Select branch: `main`
6. Build settings: Auto-detected (uses amplify.yml)
7. Review and deploy

---

## Post-Provisioning Steps

### 1. Update Environment Variables
After resources are created, update your configuration:

```bash
# Get RDS endpoint
aws rds describe-db-instances \
  --db-instance-identifier compliance-platform-db-dev \
  --query "DBInstances[0].Endpoint.Address" \
  --region ca-west-1

# Get ElastiCache endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id compliance-platform-cache-dev \
  --show-cache-node-info \
  --query "CacheClusters[0].CacheNodes[0].Endpoint.Address" \
  --region ca-west-1

# Get API Gateway endpoint
aws apigatewayv2 get-apis \
  --query "Items[?Name=='compliance-platform-api-gateway'].ApiEndpoint" \
  --region ca-west-1
```

### 2. Add GitHub Secrets
Navigate to: `https://github.com/KulbirJ/Risk-Management/settings/secrets/actions`

Add:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID`: `031195399879`

### 3. Run Database Migrations
```bash
# Connect to RDS (via bastion or VPC)
# Or run migrations via Lambda
aws lambda invoke \
  --function-name compliance-platform-api \
  --payload '{"path":"/migrate","httpMethod":"POST"}' \
  --region ca-west-1 \
  response.json
```

### 4. Test Deployment
```bash
# Test Lambda function
curl https://YOUR_API_GATEWAY_ENDPOINT/health

# Test Amplify frontend
curl https://YOUR_AMPLIFY_URL
```

### 5. Deploy Code via CI/CD
```bash
git add .
git commit -m "feat: Phase 1 serverless architecture"
git push origin main
```

This triggers the GitHub Actions workflow which will:
- Run tests
- Package Lambda function
- Deploy to AWS Lambda
- Trigger Amplify build

---

## Scaling Considerations

### When to upgrade from Phase 1:

**Traffic Thresholds:**
- \> 100K API requests/day
- \> 10 concurrent users
- \> 1GB RAM needed for Lambda
- Consistent database CPU > 80%

**Cost Threshold:**
- Monthly AWS bill > $60

**Migration Path to ECS (Phase 2):**
1. Keep RDS and ElastiCache (already sized correctly)
2. Deploy backend to ECS Fargate (t4g.small)
3. Keep Amplify for frontend
4. Add Application Load Balancer
5. Estimated new cost: $50-80/month

---

## Monitoring and Alerts

### CloudWatch Dashboards (Free Tier)
- Lambda invocations, errors, duration
- RDS CPU, connections, storage
- ElastiCache CPU, memory, connections
- API Gateway requests, latency, errors

### Recommended Alarms:
```bash
# Lambda errors > 5 in 5 minutes
# RDS CPU > 80% for 10 minutes
# ElastiCache memory > 90%
# API Gateway 5xx errors > 10 in 5 minutes
```

---

## Security Best Practices

1. **Database**: No public access, strong password, encrypted at rest
2. **Lambda**: Minimal IAM permissions, environment variables for secrets
3. **S3**: Private bucket, versioning enabled, encryption enabled
4. **API Gateway**: CORS configured, rate limiting enabled
5. **Secrets Manager**: Rotate credentials every 90 days (manual in Phase 1)

---

## Cleanup Instructions

To delete all resources and stop charges:

```bash
# Delete Lambda
aws lambda delete-function --function-name compliance-platform-api --region ca-west-1

# Delete API Gateway
aws apigatewayv2 delete-api --api-id YOUR_API_ID --region ca-west-1

# Delete RDS
aws rds delete-db-instance \
  --db-instance-identifier compliance-platform-db-dev \
  --skip-final-snapshot \
  --region ca-west-1

# Delete ElastiCache
aws elasticache delete-cache-cluster \
  --cache-cluster-id compliance-platform-cache-dev \
  --region ca-west-1

# Delete S3 bucket (empty first)
aws s3 rm s3://compliance-platform-evidence-dev --recursive
aws s3 rb s3://compliance-platform-evidence-dev --region ca-west-1

# Delete Amplify app (via console or CLI)
aws amplify delete-app --app-id YOUR_APP_ID --region ca-west-1
```

---

## Support and Troubleshooting

### Common Issues:

**Lambda timeout errors:**
- Increase timeout from 30s to 60s
- Increase memory from 512MB to 1024MB

**RDS connection errors:**
- Check security group allows Lambda subnet
- Verify DATABASE_URL is correct
- Check RDS is in same VPC as Lambda

**API Gateway 502 errors:**
- Check Lambda function logs in CloudWatch
- Verify Lambda has correct permissions
- Check Mangum adapter is installed

**Amplify build failures:**
- Check build logs in Amplify console
- Verify amplify.yml is present
- Check Node.js version compatibility

---

## Contact and Resources

- **AWS Documentation**: https://docs.aws.amazon.com
- **Amplify Docs**: https://docs.amplify.aws
- **Lambda Docs**: https://docs.aws.amazon.com/lambda
- **Cost Calculator**: https://calculator.aws
