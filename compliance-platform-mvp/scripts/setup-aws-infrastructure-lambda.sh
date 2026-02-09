#!/bin/bash
# AWS Infrastructure Setup Script for Phase 1 Serverless Architecture
# Compliance Platform MVP - Development/Testing Environment
# Estimated Cost: $25-40/month

set -e

ENVIRONMENT="${1:-dev}"
REGION="${2:-ca-west-1}"
PROJECT_NAME="compliance-platform"

echo "========================================"
echo "AWS Infrastructure Setup - Phase 1"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "========================================"
echo

# Variables
DB_NAME="${PROJECT_NAME}-db-${ENVIRONMENT}"
CACHE_NAME="${PROJECT_NAME}-cache-${ENVIRONMENT}"
BUCKET_NAME="${PROJECT_NAME}-evidence-${ENVIRONMENT}"
LAMBDA_NAME="${PROJECT_NAME}-api"
API_GATEWAY_NAME="${PROJECT_NAME}-api-gateway"
AMPLIFY_APP_NAME="${PROJECT_NAME}-frontend"
DB_USERNAME="complianceadmin"

# Generate or prompt for password
read -sp "Enter database password (or press Enter to generate): " DB_PASSWORD
echo
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(openssl rand -base64 12)
    echo "Generated database password: $DB_PASSWORD"
    echo "IMPORTANT: Save this password securely!"
fi

echo
echo "[1/8] Creating VPC and Security Groups..."

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)

if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
    echo "No default VPC found. Creating one..."
    aws ec2 create-default-vpc --region $REGION
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)
fi

echo "VPC ID: $VPC_ID"

# Get subnets
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text --region $REGION)
echo "Subnets: $SUBNET_IDS"

# Create security group for RDS
echo
echo "Creating security group for RDS..."
RDS_SG_ID=$(aws ec2 create-security-group \
    --group-name "${PROJECT_NAME}-rds-sg-${ENVIRONMENT}" \
    --description "Security group for RDS PostgreSQL" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query "GroupId" \
    --output text)

aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0 \
    --region $REGION

echo "RDS Security Group: $RDS_SG_ID"

# Create security group for ElastiCache
echo
echo "Creating security group for ElastiCache..."
CACHE_SG_ID=$(aws ec2 create-security-group \
    --group-name "${PROJECT_NAME}-cache-sg-${ENVIRONMENT}" \
    --description "Security group for ElastiCache Redis" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query "GroupId" \
    --output text)

aws ec2 authorize-security-group-ingress \
    --group-id $CACHE_SG_ID \
    --protocol tcp \
    --port 6379 \
    --cidr 0.0.0.0/0 \
    --region $REGION

echo "Cache Security Group: $CACHE_SG_ID"

echo
echo "[2/8] Creating RDS PostgreSQL Instance..."
echo "This may take 5-10 minutes..."

DB_SUBNET_GROUP="${PROJECT_NAME}-db-subnet-group-${ENVIRONMENT}"
aws rds create-db-subnet-group \
    --db-subnet-group-name $DB_SUBNET_GROUP \
    --db-subnet-group-description "Subnet group for compliance platform" \
    --subnet-ids $SUBNET_IDS \
    --region $REGION

aws rds create-db-instance \
    --db-instance-identifier $DB_NAME \
    --db-instance-class db.t4g.micro \
    --engine postgres \
    --engine-version 15.5 \
    --master-username $DB_USERNAME \
    --master-user-password "$DB_PASSWORD" \
    --allocated-storage 20 \
    --storage-type gp3 \
    --vpc-security-group-ids $RDS_SG_ID \
    --db-subnet-group-name $DB_SUBNET_GROUP \
    --backup-retention-period 7 \
    --no-publicly-accessible \
    --region $REGION

echo "RDS instance creation initiated: $DB_NAME"

echo
echo "[3/8] Creating ElastiCache Redis Cluster..."

CACHE_SUBNET_GROUP="${PROJECT_NAME}-cache-subnet-group-${ENVIRONMENT}"
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name $CACHE_SUBNET_GROUP \
    --cache-subnet-group-description "Subnet group for compliance platform cache" \
    --subnet-ids $SUBNET_IDS \
    --region $REGION

aws elasticache create-cache-cluster \
    --cache-cluster-id $CACHE_NAME \
    --cache-node-type cache.t4g.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --cache-subnet-group-name $CACHE_SUBNET_GROUP \
    --security-group-ids $CACHE_SG_ID \
    --region $REGION

echo "ElastiCache cluster creation initiated: $CACHE_NAME"

echo
echo "[4/8] Creating S3 Bucket..."

aws s3 mb "s3://${BUCKET_NAME}" --region $REGION

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled \
    --region $REGION

# Set lifecycle policy
cat > /tmp/s3-lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldEvidenceFiles",
      "Status": "Enabled",
      "Expiration": {
        "Days": 365
      },
      "Filter": {
        "Prefix": "evidence/"
      }
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket $BUCKET_NAME \
    --lifecycle-configuration file:///tmp/s3-lifecycle.json \
    --region $REGION

rm /tmp/s3-lifecycle.json

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
    --region $REGION

echo "S3 bucket created: s3://${BUCKET_NAME}"

echo
echo "[5/8] Waiting for RDS to be available..."
aws rds wait db-instance-available --db-instance-identifier $DB_NAME --region $REGION
echo "RDS instance is available!"

# Get RDS endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_NAME \
    --query "DBInstances[0].Endpoint.Address" \
    --output text \
    --region $REGION)

echo "RDS Endpoint: $DB_ENDPOINT"

echo
echo "[6/8] Creating Lambda Function..."

# Create IAM role
echo "Creating IAM role for Lambda..."
LAMBDA_ROLE_NAME="${PROJECT_NAME}-lambda-role"

cat > /tmp/lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

LAMBDA_ROLE_ARN=$(aws iam create-role \
    --role-name $LAMBDA_ROLE_NAME \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --query "Role.Arn" \
    --output text)

rm /tmp/lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess"

aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn "arn:aws:iam::aws:policy/SecretsManagerReadWrite"

# Wait for role propagation
sleep 10

# Wait for ElastiCache
echo "Waiting for ElastiCache to be available..."
while true; do
    CACHE_STATUS=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id $CACHE_NAME \
        --query "CacheClusters[0].CacheClusterStatus" \
        --output text \
        --region $REGION)
    echo "Cache status: $CACHE_STATUS"
    if [ "$CACHE_STATUS" == "available" ]; then
        break
    fi
    sleep 10
done

CACHE_ENDPOINT=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id $CACHE_NAME \
    --show-cache-node-info \
    --query "CacheClusters[0].CacheNodes[0].Endpoint.Address" \
    --output text \
    --region $REGION)

echo "Cache Endpoint: $CACHE_ENDPOINT"

# Create placeholder Lambda
echo "Creating Lambda function..."
cat > /tmp/lambda-placeholder.py <<EOF
def lambda_handler(event, context):
    return {'statusCode': 200, 'body': 'Placeholder - Deploy via CI/CD'}
EOF

cd /tmp
zip lambda-placeholder.zip lambda-placeholder.py
rm lambda-placeholder.py

DATABASE_URL="postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_ENDPOINT}:5432/postgres"
REDIS_URL="redis://${CACHE_ENDPOINT}:6379/0"

aws lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime python3.11 \
    --role $LAMBDA_ROLE_ARN \
    --handler app.main.lambda_handler \
    --zip-file fileb://lambda-placeholder.zip \
    --timeout 30 \
    --memory-size 512 \
    --environment "Variables={DATABASE_URL=$DATABASE_URL,REDIS_URL=$REDIS_URL,AWS_REGION_NAME=$REGION,S3_BUCKET_NAME=$BUCKET_NAME,ENVIRONMENT=$ENVIRONMENT}" \
    --region $REGION

rm lambda-placeholder.zip

echo "Lambda function created: $LAMBDA_NAME"

echo
echo "[7/8] Creating API Gateway..."

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

API_ID=$(aws apigatewayv2 create-api \
    --name $API_GATEWAY_NAME \
    --protocol-type HTTP \
    --target "arn:aws:lambda:${REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_NAME}" \
    --region $REGION \
    --query "ApiId" \
    --output text)

# Grant permission
aws lambda add-permission \
    --function-name $LAMBDA_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*" \
    --region $REGION

API_ENDPOINT=$(aws apigatewayv2 get-api \
    --api-id $API_ID \
    --query "ApiEndpoint" \
    --output text \
    --region $REGION)

echo "API Gateway created: $API_ENDPOINT"

echo
echo "[8/8] Creating Secrets Manager entries..."

SECRET_NAME="${PROJECT_NAME}/${ENVIRONMENT}/database"
SECRET_VALUE=$(cat <<EOF
{
  "username": "$DB_USERNAME",
  "password": "$DB_PASSWORD",
  "host": "$DB_ENDPOINT",
  "port": 5432,
  "dbname": "postgres",
  "url": "$DATABASE_URL"
}
EOF
)

aws secretsmanager create-secret \
    --name $SECRET_NAME \
    --description "Database credentials for compliance platform" \
    --secret-string "$SECRET_VALUE" \
    --region $REGION

echo "Secret created: $SECRET_NAME"

echo
echo "========================================"
echo "Infrastructure Setup Complete!"
echo "========================================"
echo

echo "Resource Summary:"
echo "  VPC ID: $VPC_ID"
echo "  RDS Endpoint: $DB_ENDPOINT"
echo "  Cache Endpoint: $CACHE_ENDPOINT"
echo "  S3 Bucket: s3://${BUCKET_NAME}"
echo "  Lambda Function: $LAMBDA_NAME"
echo "  API Gateway: $API_ENDPOINT"
echo "  Secrets Manager: $SECRET_NAME"

echo
echo "Next Steps:"
echo "  1. Add these GitHub Secrets:"
echo "     - AWS_ACCESS_KEY_ID"
echo "     - AWS_SECRET_ACCESS_KEY"
echo "     - AWS_ACCOUNT_ID"
echo "  2. Update .env files with:"
echo "     - DATABASE_URL=$DATABASE_URL"
echo "     - REDIS_URL=$REDIS_URL"
echo "     - NEXT_PUBLIC_API_URL=$API_ENDPOINT"
echo "     - S3_BUCKET_NAME=$BUCKET_NAME"
echo "  3. Deploy frontend with AWS Amplify Console (connect GitHub repo)"
echo "  4. Push code to trigger CI/CD Lambda deployment"

echo
echo "Estimated Monthly Cost: \$25-40"
echo "  - RDS t4g.micro: ~\$12-15"
echo "  - ElastiCache t4g.micro: ~\$8-10"
echo "  - Lambda: ~\$2-5 (10K-50K requests)"
echo "  - S3: ~\$1-3 (500MB storage)"
echo "  - API Gateway: ~\$1-2"
echo "  - Amplify: ~\$1-5"

echo
echo "Setup completed successfully!"
