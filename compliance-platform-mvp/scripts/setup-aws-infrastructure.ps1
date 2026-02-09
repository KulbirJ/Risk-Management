# AWS Infrastructure Setup Script for Compliance Platform
# This script automates the creation of AWS resources for CI/CD deployment

param(
    [string]$AWSAccountId = "031195399879",
    [string]$AWSRegion = "ca-west-1",
    [string]$GitHubRepo = "KulbirJ/Risk-Management",
    [string]$ECRRepoName = "compliance-platform-mvp",
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Continue"

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "AWS Infrastructure Setup Script" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  AWS Account ID: $AWSAccountId"
Write-Host "  AWS Region: $AWSRegion"
Write-Host "  GitHub Repo: $GitHubRepo"
Write-Host "  ECR Repository: $ECRRepoName"
Write-Host "  Dry Run: $DryRun`n"

if ($DryRun) {
    Write-Host "DRY RUN MODE - No changes will be made`n" -ForegroundColor Yellow
}

# Function to check if AWS CLI is installed
function Test-AWSCli {
    try {
        $null = aws --version 2>$null
        return $true
    } catch {
        return $false
    }
}

# Step 0: Pre-flight checks
Write-Host "Step 0: Pre-flight checks..." -ForegroundColor Green

if (-not (Test-AWSCli)) {
    Write-Host "ERROR: AWS CLI is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install AWS CLI: https://aws.amazon.com/cli/" -ForegroundColor Yellow
    exit 1
}
Write-Host "  [OK] AWS CLI is installed" -ForegroundColor Green

try {
    $callerIdentity = aws sts get-caller-identity --region $AWSRegion 2>&1 | ConvertFrom-Json
    Write-Host "  [OK] AWS credentials are configured" -ForegroundColor Green
    Write-Host "  [OK] Connected as: $($callerIdentity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS credentials are not configured" -ForegroundColor Red
    Write-Host "Please run: aws configure" -ForegroundColor Yellow
    exit 1
}

# Step 1: Create OIDC Provider for GitHub Actions
Write-Host "`nStep 1: Creating OIDC Provider for GitHub Actions..." -ForegroundColor Green

$oidcThumbprint = "6938fd4d98bab03faadb97b34396831e3780aea1"
$oidcUrl = "https://token.actions.githubusercontent.com"

try {
    $existingProvider = aws iam list-open-id-connect-providers --region $AWSRegion 2>&1 | ConvertFrom-Json
    $providerExists = $existingProvider.OpenIDConnectProviderList | Where-Object { $_.Arn -like "*token.actions.githubusercontent.com*" }

    if ($providerExists) {
        Write-Host "  [OK] OIDC Provider already exists" -ForegroundColor Yellow
    } else {
        if (-not $DryRun) {
            aws iam create-open-id-connect-provider --url $oidcUrl --client-id-list sts.amazonaws.com --thumbprint-list $oidcThumbprint --region $AWSRegion 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] OIDC Provider created" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] OIDC Provider might already exist" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  [DRY RUN] Would create OIDC Provider" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "  [WARN] Could not verify OIDC Provider" -ForegroundColor Yellow
}

# Step 2: Create IAM Role for GitHub Actions
Write-Host "`nStep 2: Creating IAM Role for GitHub Actions..." -ForegroundColor Green

$roleName = "github-actions-role"
$trustPolicyPath = "github-actions-trust-policy.json"

# Create trust policy JSON
$trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWSAccountId}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GitHubRepo}:*"
        }
      }
    }
  ]
}
"@

$trustPolicy | Out-File -FilePath $trustPolicyPath -Encoding UTF8

$roleExists = aws iam get-role --role-name $roleName --region $AWSRegion 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] IAM Role already exists" -ForegroundColor Yellow
} else {
    if (-not $DryRun) {
        $roleResult = aws iam create-role --role-name $roleName --assume-role-policy-document file://$trustPolicyPath --description "Role for GitHub Actions" --region $AWSRegion 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] IAM Role created: $roleName" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to create IAM Role" -ForegroundColor Red
            Write-Host "  Error details: $roleResult" -ForegroundColor Red
        }
    } else {
        Write-Host "  [DRY RUN] Would create IAM Role" -ForegroundColor Cyan
    }
}

# Step 3: Create and Attach IAM Policy
Write-Host "`nStep 3: Creating IAM Policy for ECR and ECS..." -ForegroundColor Green

$policyName = "GitHubActionsDeployPolicy"
$policyPath = "github-actions-permissions.json"

$policy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:${AWSRegion}:${AWSAccountId}:repository/${ECRRepoName}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:UpdateService",
        "ecs:RegisterTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::${AWSAccountId}:role/ecsTaskExecutionRole"
    }
  ]
}
"@

$policy | Out-File -FilePath $policyPath -Encoding UTF8

try {
    $existingPolicy = aws iam list-policies --scope Local --region $AWSRegion 2>&1 | ConvertFrom-Json
    $policyArn = $existingPolicy.Policies | Where-Object { $_.PolicyName -eq $policyName } | Select-Object -ExpandProperty Arn

    if ($policyArn) {
        Write-Host "  [OK] Policy already exists: $policyName" -ForegroundColor Yellow
    } else {
        if (-not $DryRun) {
            $result = aws iam create-policy --policy-name $policyName --policy-document file://$policyPath --description "Policy for GitHub Actions" --region $AWSRegion 2>&1 | ConvertFrom-Json
            $policyArn = $result.Policy.Arn
            Write-Host "  [OK] Policy created: $policyName" -ForegroundColor Green
        } else {
            Write-Host "  [DRY RUN] Would create policy" -ForegroundColor Cyan
            $policyArn = "arn:aws:iam::${AWSAccountId}:policy/${policyName}"
        }
    }

    # Attach policy to role
    if ($policyArn -and -not $DryRun) {
        aws iam attach-role-policy --role-name $roleName --policy-arn $policyArn --region $AWSRegion 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Policy attached to role" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Policy might already be attached" -ForegroundColor Yellow
        }
    } elseif ($DryRun) {
        Write-Host "  [DRY RUN] Would attach policy to role" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  [WARN] Error creating or attaching policy" -ForegroundColor Yellow
}

# Step 4: Create ECR Repository
Write-Host "`nStep 4: Creating ECR Repository..." -ForegroundColor Green

$ecrExists = aws ecr describe-repositories --repository-names $ECRRepoName --region $AWSRegion 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] ECR Repository already exists: $ECRRepoName" -ForegroundColor Yellow
} else {
    if (-not $DryRun) {
        aws ecr create-repository --repository-name $ECRRepoName --region $AWSRegion --image-scanning-configuration scanOnPush=true --encryption-configuration encryptionType=AES256 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] ECR Repository created: $ECRRepoName" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to create ECR Repository" -ForegroundColor Red
        }
    } else {
        Write-Host "  [DRY RUN] Would create ECR Repository" -ForegroundColor Cyan
    }
}

# Step 5: Create ECS Task Execution Role
Write-Host "`nStep 5: Creating ECS Task Execution Role..." -ForegroundColor Green

$ecsRoleName = "ecsTaskExecutionRole"
$ecsTrustPolicyPath = "ecs-task-trust-policy.json"

$ecsTrustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@

$ecsTrustPolicy | Out-File -FilePath $ecsTrustPolicyPath -Encoding UTF8

$ecsRoleExists = aws iam get-role --role-name $ecsRoleName --region $AWSRegion 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] ECS Task Execution Role already exists" -ForegroundColor Yellow
} else {
    if (-not $DryRun) {
        $ecsRoleResult = aws iam create-role --role-name $ecsRoleName --assume-role-policy-document file://$ecsTrustPolicyPath --description "ECS Task Execution Role" --region $AWSRegion 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] ECS Task Execution Role created" -ForegroundColor Green
            
            # Attach managed policy
            aws iam attach-role-policy --role-name $ecsRoleName --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy --region $AWSRegion 2>&1 | Out-Null
            Write-Host "  [OK] AmazonECSTaskExecutionRolePolicy attached" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to create ECS Task Execution Role" -ForegroundColor Red
            Write-Host "  Error details: $ecsRoleResult" -ForegroundColor Red
        }
    } else {
        Write-Host "  [DRY RUN] Would create ECS Task Execution Role" -ForegroundColor Cyan
    }
}

# Step 6: Create CloudWatch Log Group
Write-Host "`nStep 6: Creating CloudWatch Log Group..." -ForegroundColor Green

$logGroupName = "/ecs/compliance-platform-staging"
try {
    $logGroupExists = aws logs describe-log-groups --log-group-name-prefix $logGroupName --region $AWSRegion 2>&1 | ConvertFrom-Json
    if ($logGroupExists.logGroups.Count -gt 0) {
        Write-Host "  [OK] Log Group already exists: $logGroupName" -ForegroundColor Yellow
    } else {
        if (-not $DryRun) {
            aws logs create-log-group --log-group-name $logGroupName --region $AWSRegion 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Log Group created: $logGroupName" -ForegroundColor Green
                
                # Set retention policy
                aws logs put-retention-policy --log-group-name $logGroupName --retention-in-days 7 --region $AWSRegion 2>&1 | Out-Null
                Write-Host "  [OK] Retention policy set to 7 days" -ForegroundColor Green
            } else {
                Write-Host "  [ERROR] Failed to create Log Group" -ForegroundColor Red
            }
        } else {
            Write-Host "  [DRY RUN] Would create Log Group" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "  [WARN] Could not verify Log Group" -ForegroundColor Yellow
}

# Step 7: Create ECS Cluster
Write-Host "`nStep 7: Creating ECS Cluster..." -ForegroundColor Green

$clusterName = "compliance-platform-staging"
try {
    $clusterExists = aws ecs describe-clusters --clusters $clusterName --region $AWSRegion 2>&1 | ConvertFrom-Json
    if ($clusterExists.clusters.Count -gt 0 -and $clusterExists.clusters[0].status -eq "ACTIVE") {
        Write-Host "  [OK] ECS Cluster already exists: $clusterName" -ForegroundColor Yellow
    } else {
        if (-not $DryRun) {
            $clusterResult = aws ecs create-cluster --cluster-name $clusterName --region $AWSRegion --capacity-providers FARGATE FARGATE_SPOT --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] ECS Cluster created: $clusterName" -ForegroundColor Green
            } else {
                Write-Host "  [ERROR] Failed to create ECS Cluster" -ForegroundColor Red
                Write-Host "  Error details: $clusterResult" -ForegroundColor Red
            }
        } else {
            Write-Host "  [DRY RUN] Would create ECS Cluster" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "  [WARN] Could not verify ECS Cluster" -ForegroundColor Yellow
}

# Cleanup temporary files
if (Test-Path $trustPolicyPath) { Remove-Item $trustPolicyPath }
if (Test-Path $policyPath) { Remove-Item $policyPath }
if (Test-Path $ecsTrustPolicyPath) { Remove-Item $ecsTrustPolicyPath }

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Configure GitHub Secrets at:" -ForegroundColor White
Write-Host "   https://github.com/${GitHubRepo}/settings/secrets/actions" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Add these secrets:" -ForegroundColor White
Write-Host "   - AWS_ACCOUNT_ID: $AWSAccountId" -ForegroundColor Gray
Write-Host "   - AWS_REGION: $AWSRegion" -ForegroundColor Gray
Write-Host "   - AWS_ROLE_ARN: arn:aws:iam::${AWSAccountId}:role/$roleName" -ForegroundColor Gray
Write-Host "   - ECR_REPOSITORY: $ECRRepoName" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Push code to GitHub to trigger CI/CD pipeline" -ForegroundColor White
Write-Host ""
Write-Host "3. View your ECR repository:" -ForegroundColor White
Write-Host "   aws ecr describe-repositories --repository-names $ECRRepoName --region $AWSRegion" -ForegroundColor Cyan
Write-Host ""
Write-Host "Resources Created:" -ForegroundColor Yellow
Write-Host "  [OK] OIDC Provider for GitHub Actions" -ForegroundColor Green
Write-Host "  [OK] IAM Role: $roleName" -ForegroundColor Green
Write-Host "  [OK] IAM Policy: $policyName" -ForegroundColor Green
Write-Host "  [OK] ECR Repository: $ECRRepoName" -ForegroundColor Green
Write-Host "  [OK] ECS Task Execution Role: $ecsRoleName" -ForegroundColor Green
Write-Host "  [OK] CloudWatch Log Group: $logGroupName" -ForegroundColor Green
Write-Host "  [OK] ECS Cluster: $clusterName" -ForegroundColor Green
Write-Host ""
