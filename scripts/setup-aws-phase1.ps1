# AWS Infrastructure Setup Script for Phase 1 Serverless Architecture
# Compliance Platform MVP - Development/Testing Environment
# Estimated Cost: $25-40/month

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "ca-west-1",
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectName = "compliance-platform",
    
    [Parameter(Mandatory=$false)]
    [string]$DBPassword = ""
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "AWS Infrastructure Setup - Phase 1" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check AWS CLI
Write-Host "Checking AWS CLI..." -ForegroundColor Yellow
try {
    $awsVersion = aws --version
    Write-Host "AWS CLI found: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS CLI not found. Please install AWS CLI first." -ForegroundColor Red
    exit 1
}

# Check AWS credentials
Write-Host "Checking AWS credentials..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --region $Region | ConvertFrom-Json
    Write-Host "Authenticated as: $($identity.Arn)" -ForegroundColor Green
    Write-Host "Account ID: $($identity.Account)`n" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS credentials not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Variables
$dbName = "${ProjectName}-db-${Environment}"
$cacheName = "${ProjectName}-cache-${Environment}"
$bucketName = "${ProjectName}-evidence-${Environment}"
$lambdaName = "${ProjectName}-api"
$apiGatewayName = "${ProjectName}-api-gateway"
$dbUsername = "complianceadmin"

# Handle password
if ([string]::IsNullOrWhiteSpace($DBPassword)) {
    $securePassword = Read-Host -Prompt "Enter database password (or press Enter to generate)" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $DBPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    
    if ([string]::IsNullOrWhiteSpace($DBPassword)) {
        $DBPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object {[char]$_})
        Write-Host "Generated database password: $DBPassword" -ForegroundColor Yellow
        Write-Host "IMPORTANT: Save this password securely!" -ForegroundColor Red
    }
}

Write-Host "`n[1/8] Creating VPC and Security Groups..." -ForegroundColor Green

# Get default VPC
$vpcId = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $Region

if ([string]::IsNullOrWhiteSpace($vpcId) -or $vpcId -eq "None") {
    Write-Host "No default VPC found. Creating one..." -ForegroundColor Yellow
    aws ec2 create-default-vpc --region $Region
    Start-Sleep -Seconds 5
    $vpcId = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $Region
}

Write-Host "VPC ID: $vpcId"

# Get subnets
$subnetIds = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[*].SubnetId" --output text --region $Region
$subnetArray = $subnetIds -split "\s+"
Write-Host "Subnets: $($subnetArray -join ', ')"

# Create security group for RDS
Write-Host "`nChecking RDS security group..." -ForegroundColor Yellow
$rdsSecurityGroupId = aws ec2 describe-security-groups `
    --filters "Name=group-name,Values=${ProjectName}-rds-sg-${Environment}" "Name=vpc-id,Values=$vpcId" `
    --query "SecurityGroups[0].GroupId" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($rdsSecurityGroupId) -or $rdsSecurityGroupId -eq "None") {
    Write-Host "Creating new RDS security group..." -ForegroundColor Yellow
    $rdsSecurityGroupId = aws ec2 create-security-group `
        --group-name "${ProjectName}-rds-sg-${Environment}" `
        --description "Security group for RDS PostgreSQL" `
        --vpc-id $vpcId `
        --region $Region `
        --query "GroupId" `
        --output text

    Start-Sleep -Seconds 2

    aws ec2 authorize-security-group-ingress `
        --group-id $rdsSecurityGroupId `
        --protocol tcp `
        --port 5432 `
        --cidr 0.0.0.0/0 `
        --region $Region 2>$null

    Write-Host "✓ Created RDS Security Group: $rdsSecurityGroupId" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing RDS Security Group: $rdsSecurityGroupId" -ForegroundColor Green
}

# Create security group for ElastiCache
Write-Host "`nChecking ElastiCache security group..." -ForegroundColor Yellow
$cacheSecurityGroupId = aws ec2 describe-security-groups `
    --filters "Name=group-name,Values=${ProjectName}-cache-sg-${Environment}" "Name=vpc-id,Values=$vpcId" `
    --query "SecurityGroups[0].GroupId" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($cacheSecurityGroupId) -or $cacheSecurityGroupId -eq "None") {
    Write-Host "Creating new ElastiCache security group..." -ForegroundColor Yellow
    $cacheSecurityGroupId = aws ec2 create-security-group `
        --group-name "${ProjectName}-cache-sg-${Environment}" `
        --description "Security group for ElastiCache Redis" `
        --vpc-id $vpcId `
        --region $Region `
        --query "GroupId" `
        --output text

    Start-Sleep -Seconds 2

    aws ec2 authorize-security-group-ingress `
        --group-id $cacheSecurityGroupId `
        --protocol tcp `
        --port 6379 `
        --cidr 0.0.0.0/0 `
        --region $Region 2>$null

    Write-Host "✓ Created Cache Security Group: $cacheSecurityGroupId" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing Cache Security Group: $cacheSecurityGroupId" -ForegroundColor Green
}

Write-Host "`n[2/8] Creating RDS PostgreSQL Instance..." -ForegroundColor Green

$dbSubnetGroupName = "${ProjectName}-db-subnet-group-${Environment}"

# Check if DB subnet group exists
Write-Host "Checking DB subnet group..." -ForegroundColor Yellow
$existingDbSubnetGroup = aws rds describe-db-subnet-groups `
    --db-subnet-group-name $dbSubnetGroupName `
    --query "DBSubnetGroups[0].DBSubnetGroupName" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($existingDbSubnetGroup) -or $existingDbSubnetGroup -eq "None") {
    Write-Host "Creating DB subnet group..." -ForegroundColor Yellow
    aws rds create-db-subnet-group `
        --db-subnet-group-name $dbSubnetGroupName `
        --db-subnet-group-description "Subnet group for compliance platform" `
        --subnet-ids $subnetArray `
        --region $Region | Out-Null
    Write-Host "✓ Created DB subnet group: $dbSubnetGroupName" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing DB subnet group: $dbSubnetGroupName" -ForegroundColor Green
}

# Check if RDS instance exists
Write-Host "Checking RDS instance..." -ForegroundColor Yellow
$existingRdsInstance = aws rds describe-db-instances `
    --db-instance-identifier $dbName `
    --query "DBInstances[0].DBInstanceIdentifier" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($existingRdsInstance) -or $existingRdsInstance -eq "None") {
    Write-Host "Creating RDS instance (this takes 5-10 minutes)..." -ForegroundColor Yellow
    aws rds create-db-instance `
        --db-instance-identifier $dbName `
        --db-instance-class db.t4g.micro `
        --engine postgres `
        --engine-version 15.5 `
        --master-username $dbUsername `
        --master-user-password $DBPassword `
        --allocated-storage 20 `
        --storage-type gp3 `
        --vpc-security-group-ids $rdsSecurityGroupId `
        --db-subnet-group-name $dbSubnetGroupName `
        --backup-retention-period 7 `
        --no-publicly-accessible `
        --region $Region | Out-Null

    Write-Host "✓ RDS instance creation initiated: $dbName" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing RDS instance: $dbName" -ForegroundColor Green
}

Write-Host "`n[3/8] Creating ElastiCache Redis Cluster..." -ForegroundColor Green

$cacheSubnetGroupName = "${ProjectName}-cache-subnet-group-${Environment}"

# Check if cache subnet group exists
Write-Host "Checking cache subnet group..." -ForegroundColor Yellow
$existingCacheSubnetGroup = aws elasticache describe-cache-subnet-groups `
    --cache-subnet-group-name $cacheSubnetGroupName `
    --query "CacheSubnetGroups[0].CacheSubnetGroupName" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($existingCacheSubnetGroup) -or $existingCacheSubnetGroup -eq "None") {
    Write-Host "Creating cache subnet group..." -ForegroundColor Yellow
    aws elasticache create-cache-subnet-group `
        --cache-subnet-group-name $cacheSubnetGroupName `
        --cache-subnet-group-description "Subnet group for compliance platform cache" `
        --subnet-ids $subnetArray `
        --region $Region | Out-Null
    Write-Host "✓ Created cache subnet group: $cacheSubnetGroupName" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing cache subnet group: $cacheSubnetGroupName" -ForegroundColor Green
}

# Check if ElastiCache cluster exists
Write-Host "Checking ElastiCache cluster..." -ForegroundColor Yellow
$existingCacheCluster = aws elasticache describe-cache-clusters `
    --cache-cluster-id $cacheName `
    --query "CacheClusters[0].CacheClusterId" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($existingCacheCluster) -or $existingCacheCluster -eq "None") {
    Write-Host "Creating ElastiCache cluster (this takes 5-10 minutes)..." -ForegroundColor Yellow
    aws elasticache create-cache-cluster `
        --cache-cluster-id $cacheName `
        --cache-node-type cache.t4g.micro `
        --engine redis `
        --num-cache-nodes 1 `
        --cache-subnet-group-name $cacheSubnetGroupName `
        --security-group-ids $cacheSecurityGroupId `
        --region $Region | Out-Null

    Write-Host "✓ ElastiCache cluster creation initiated: $cacheName" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing ElastiCache cluster: $cacheName" -ForegroundColor Green
}

Write-Host "`n[4/8] Creating S3 Bucket..." -ForegroundColor Green

# Check if S3 bucket exists
Write-Host "Checking S3 bucket..." -ForegroundColor Yellow
$bucketExists = aws s3api head-bucket --bucket $bucketName --region $Region 2>$null
$bucketExistsCheck = $?

if (-not $bucketExistsCheck) {
    Write-Host "Creating S3 bucket..." -ForegroundColor Yellow
    aws s3 mb "s3://${bucketName}" --region $Region
    Write-Host "✓ Created S3 bucket: s3://${bucketName}" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing S3 bucket: s3://${bucketName}" -ForegroundColor Green
}

# Configure bucket settings (these are idempotent)
Write-Host "Configuring S3 bucket settings..." -ForegroundColor Yellow

# Enable versioning
aws s3api put-bucket-versioning `
    --bucket $bucketName `
    --versioning-configuration Status=Enabled `
    --region $Region

# Set lifecycle policy
$lifecyclePolicy = @"
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
"@

$lifecyclePolicy | Out-File -FilePath "$env:TEMP\s3-lifecycle.json" -Encoding utf8 -NoNewline
aws s3api put-bucket-lifecycle-configuration `
    --bucket $bucketName `
    --lifecycle-configuration "file://$env:TEMP\s3-lifecycle.json" `
    --region $Region
Remove-Item "$env:TEMP\s3-lifecycle.json" -ErrorAction SilentlyContinue

# Enable encryption
aws s3api put-bucket-encryption `
    --bucket $bucketName `
    --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}' `
    --region $Region

Write-Host "S3 bucket configured with versioning, lifecycle, and encryption" -ForegroundColor Green

Write-Host "`n[5/8] Waiting for RDS to be available..." -ForegroundColor Green
Write-Host "This will take several minutes. Checking status every 30 seconds..."

$maxAttempts = 20
$attempt = 0
$rdsReady = $false

while ($attempt -lt $maxAttempts -and -not $rdsReady) {
    $attempt++
    Start-Sleep -Seconds 30
    
    $dbStatus = aws rds describe-db-instances `
        --db-instance-identifier $dbName `
        --query "DBInstances[0].DBInstanceStatus" `
        --output text `
        --region $Region
    
    Write-Host "  Attempt $attempt/$maxAttempts - RDS Status: $dbStatus" -ForegroundColor Yellow
    
    if ($dbStatus -eq "available") {
        $rdsReady = $true
        Write-Host "RDS instance is available!" -ForegroundColor Green
    }
}

if (-not $rdsReady) {
    Write-Host "Warning: RDS is taking longer than expected. Continuing anyway..." -ForegroundColor Yellow
}

# Get RDS endpoint
$dbEndpoint = aws rds describe-db-instances `
    --db-instance-identifier $dbName `
    --query "DBInstances[0].Endpoint.Address" `
    --output text `
    --region $Region

Write-Host "RDS Endpoint: $dbEndpoint" -ForegroundColor Green

Write-Host "`n[6/8] Creating Lambda Function..." -ForegroundColor Green

# Create or get IAM role for Lambda
Write-Host "Checking Lambda IAM role..." -ForegroundColor Yellow
$lambdaRoleName = "${ProjectName}-lambda-role"
$accountId = $identity.Account

$existingRole = aws iam get-role `
    --role-name $lambdaRoleName `
    --query "Role.Arn" `
    --output text 2>$null

if ([string]::IsNullOrWhiteSpace($existingRole) -or $existingRole -eq "None") {
    Write-Host "Creating Lambda IAM role..." -ForegroundColor Yellow
    $trustPolicy = @"
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
"@

    $trustPolicy | Out-File -FilePath "$env:TEMP\lambda-trust-policy.json" -Encoding utf8 -NoNewline

    $lambdaRoleArn = aws iam create-role `
        --role-name $lambdaRoleName `
        --assume-role-policy-document "file://$env:TEMP\lambda-trust-policy.json" `
        --query "Role.Arn" `
        --output text

    Remove-Item "$env:TEMP\lambda-trust-policy.json" -ErrorAction SilentlyContinue
    Write-Host "✓ Created Lambda role: $lambdaRoleArn" -ForegroundColor Green
    
    # Wait for new role to propagate
    Write-Host "Waiting for IAM role to propagate..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
} else {
    $lambdaRoleArn = $existingRole
    Write-Host "✓ Found existing Lambda role: $lambdaRoleArn" -ForegroundColor Green
}

# Attach policies (idempotent operation)
Write-Host "Attaching IAM policies to Lambda role..." -ForegroundColor Yellow
aws iam attach-role-policy `
    --role-name $lambdaRoleName `
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>$null

aws iam attach-role-policy `
    --role-name $lambdaRoleName `
    --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" 2>$null

aws iam attach-role-policy `
    --role-name $lambdaRoleName `
    --policy-arn "arn:aws:iam::aws:policy/SecretsManagerReadWrite" 2>$null

Write-Host "✓ IAM policies attached" -ForegroundColor Green

# Wait for ElastiCache
Write-Host "`nWaiting for ElastiCache to be available..." -ForegroundColor Yellow
$cacheAttempts = 0
$cacheReady = $false

while ($cacheAttempts -lt 20 -and -not $cacheReady) {
    $cacheAttempts++
    Start-Sleep -Seconds 15
    
    $cacheStatus = aws elasticache describe-cache-clusters `
        --cache-cluster-id $cacheName `
        --query "CacheClusters[0].CacheClusterStatus" `
        --output text `
        --region $Region
    
    Write-Host "  Cache Status: $cacheStatus" -ForegroundColor Yellow
    
    if ($cacheStatus -eq "available") {
        $cacheReady = $true
        Write-Host "ElastiCache is available!" -ForegroundColor Green
    }
}

$cacheEndpoint = aws elasticache describe-cache-clusters `
    --cache-cluster-id $cacheName `
    --show-cache-node-info `
    --query "CacheClusters[0].CacheNodes[0].Endpoint.Address" `
    --output text `
    --region $Region

Write-Host "Cache Endpoint: $cacheEndpoint" -ForegroundColor Green

# Create placeholder Lambda
Write-Host "`nChecking Lambda function..." -ForegroundColor Yellow
$existingLambda = aws lambda get-function `
    --function-name $lambdaName `
    --query "Configuration.FunctionName" `
    --output text `
    --region $Region 2>$null

$databaseUrl = "postgresql://${dbUsername}:${DBPassword}@${dbEndpoint}:5432/postgres"
$redisUrl = "redis://${cacheEndpoint}:6379/0"

if ([string]::IsNullOrWhiteSpace($existingLambda) -or $existingLambda -eq "None") {
    Write-Host "Creating Lambda function..." -ForegroundColor Yellow
    $placeholderCode = @"
def lambda_handler(event, context):
    return {'statusCode': 200, 'body': 'Placeholder - Deploy via CI/CD'}
"@

    $placeholderCode | Out-File -FilePath "$env:TEMP\lambda-placeholder.py" -Encoding utf8 -NoNewline
    Compress-Archive -Path "$env:TEMP\lambda-placeholder.py" -DestinationPath "$env:TEMP\lambda-placeholder.zip" -Force
    Remove-Item "$env:TEMP\lambda-placeholder.py" -ErrorAction SilentlyContinue

    aws lambda create-function `
        --function-name $lambdaName `
        --runtime python3.11 `
        --role $lambdaRoleArn `
        --handler app.main.lambda_handler `
        --zip-file "fileb://$env:TEMP\lambda-placeholder.zip" `
        --timeout 30 `
        --memory-size 512 `
        --environment "Variables={DATABASE_URL=$databaseUrl,REDIS_URL=$redisUrl,AWS_REGION_NAME=$Region,S3_BUCKET_NAME=$bucketName,ENVIRONMENT=$Environment}" `
        --region $Region | Out-Null

    Remove-Item "$env:TEMP\lambda-placeholder.zip" -ErrorAction SilentlyContinue
    Write-Host "✓ Lambda function created: $lambdaName" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing Lambda function: $lambdaName" -ForegroundColor Green
    Write-Host "Updating Lambda configuration..." -ForegroundColor Yellow
    aws lambda update-function-configuration `
        --function-name $lambdaName `
        --environment "Variables={DATABASE_URL=$databaseUrl,REDIS_URL=$redisUrl,AWS_REGION_NAME=$Region,S3_BUCKET_NAME=$bucketName,ENVIRONMENT=$Environment}" `
        --region $Region | Out-Null
    Write-Host "✓ Lambda configuration updated" -ForegroundColor Green
}

Write-Host "`n[7/8] Creating API Gateway..." -ForegroundColor Green

# Check if API Gateway exists
Write-Host "Checking API Gateway..." -ForegroundColor Yellow
$apiId = aws apigatewayv2 get-apis `
    --query "Items[?Name=='${apiGatewayName}'].ApiId" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($apiId) -or $apiId -eq "None") {
    Write-Host "Creating API Gateway..." -ForegroundColor Yellow
    $apiId = aws apigatewayv2 create-api `
        --name $apiGatewayName `
        --protocol-type HTTP `
        --target "arn:aws:lambda:${Region}:${accountId}:function:${lambdaName}" `
        --region $Region `
        --query "ApiId" `
        --output text

    Write-Host "✓ API Gateway created with ID: $apiId" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing API Gateway: $apiId" -ForegroundColor Green
}

# Grant API Gateway permission to invoke Lambda (idempotent)
Write-Host "Configuring API Gateway permissions..." -ForegroundColor Yellow
aws lambda add-permission `
    --function-name $lambdaName `
    --statement-id apigateway-invoke `
    --action lambda:InvokeFunction `
    --principal apigateway.amazonaws.com `
    --source-arn "arn:aws:execute-api:${Region}:${accountId}:${apiId}/*" `
    --region $Region 2>$null
Write-Host "✓ API Gateway permissions configured" -ForegroundColor Green

$apiEndpoint = aws apigatewayv2 get-api `
    --api-id $apiId `
    --query "ApiEndpoint" `
    --output text `
    --region $Region

Write-Host "API Gateway Endpoint: $apiEndpoint" -ForegroundColor Green

Write-Host "`n[8/8] Creating Secrets Manager entries..." -ForegroundColor Green

$secretName = "${ProjectName}/${Environment}/database"
$secretValue = @{
    username = $dbUsername
    password = $DBPassword
    host = $dbEndpoint
    port = 5432
    dbname = "postgres"
    url = $databaseUrl
} | ConvertTo-Json

# Check if secret exists
Write-Host "Checking Secrets Manager secret..." -ForegroundColor Yellow
$existingSecret = aws secretsmanager describe-secret `
    --secret-id $secretName `
    --query "Name" `
    --output text `
    --region $Region 2>$null

if ([string]::IsNullOrWhiteSpace($existingSecret) -or $existingSecret -eq "None") {
    Write-Host "Creating secret..." -ForegroundColor Yellow
    aws secretsmanager create-secret `
        --name $secretName `
        --description "Database credentials for compliance platform" `
        --secret-string $secretValue `
        --region $Region | Out-Null

    Write-Host "✓ Secret created: $secretName" -ForegroundColor Green
} else {
    Write-Host "✓ Found existing secret: $secretName" -ForegroundColor Green
    Write-Host "Updating secret value..." -ForegroundColor Yellow
    aws secretsmanager update-secret `
        --secret-id $secretName `
        --secret-string $secretValue `
        --region $Region | Out-Null
    Write-Host "✓ Secret updated" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Infrastructure Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Resource Summary:" -ForegroundColor Yellow
Write-Host "  VPC ID: $vpcId"
Write-Host "  RDS Endpoint: $dbEndpoint"
Write-Host "  Cache Endpoint: $cacheEndpoint"
Write-Host "  S3 Bucket: s3://${bucketName}"
Write-Host "  Lambda Function: $lambdaName"
Write-Host "  API Gateway: $apiEndpoint"
Write-Host "  Secrets Manager: $secretName"

Write-Host "`nConnection Strings:" -ForegroundColor Yellow
Write-Host "  DATABASE_URL: $databaseUrl" -ForegroundColor Cyan
Write-Host "  REDIS_URL: $redisUrl" -ForegroundColor Cyan
Write-Host "  API_ENDPOINT: $apiEndpoint" -ForegroundColor Cyan

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Add these GitHub Secrets:"
Write-Host "     - AWS_ACCESS_KEY_ID"
Write-Host "     - AWS_SECRET_ACCESS_KEY"
Write-Host "     - AWS_ACCOUNT_ID: $accountId"
Write-Host "  2. Update .env files with connection strings above"
Write-Host "  3. Deploy frontend with AWS Amplify Console"
Write-Host "  4. Push code to trigger CI/CD Lambda deployment"
Write-Host "  5. Test API: curl $apiEndpoint/health"

Write-Host "`nEstimated Monthly Cost: `$25-40" -ForegroundColor Green
Write-Host "  - RDS t4g.micro: ~`$12-15"
Write-Host "  - ElastiCache t4g.micro: ~`$8-10"
Write-Host "  - Lambda: ~`$2-5 (10K-50K requests)"
Write-Host "  - S3: ~`$1-3 (500MB storage)"
Write-Host "  - API Gateway: ~`$1-2"
Write-Host "  - Amplify: ~`$1-5"

Write-Host "`nSetup completed successfully!" -ForegroundColor Green
Write-Host "Database password saved in Secrets Manager: $secretName" -ForegroundColor Yellow
