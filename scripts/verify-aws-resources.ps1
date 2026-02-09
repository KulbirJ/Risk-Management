# AWS Infrastructure Verification Script
# This script checks what resources already exist and provides next steps

param(
    [string]$AWSAccountId = "031195399879",
    [string]$AWSRegion = "ca-west-1",
    [string]$GitHubRepo = "KulbirJ/Risk-Management",
    [string]$ECRRepoName = "compliance-platform-mvp"
)

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "AWS Infrastructure Verification Script" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  AWS Account ID: $AWSAccountId"
Write-Host "  AWS Region: $AWSRegion"
Write-Host "  GitHub Repo: $GitHubRepo"
Write-Host "  ECR Repository: $ECRRepoName`n"

# Function to check if AWS CLI is installed
function Test-AWSCli {
    try {
        $null = aws --version 2>$null
        return $true
    } catch {
        return $false
    }
}

# Check AWS CLI
Write-Host "Checking AWS CLI..." -ForegroundColor Green
if (-not (Test-AWSCli)) {
    Write-Host "  [ERROR] AWS CLI is not installed or not in PATH" -ForegroundColor Red
    Write-Host "`nPlease install AWS CLI from: https://aws.amazon.com/cli/" -ForegroundColor Yellow
    exit 1
}
Write-Host "  [OK] AWS CLI is installed" -ForegroundColor Green

# Check AWS credentials
try {
    $callerIdentity = aws sts get-caller-identity --region $AWSRegion 2>&1 | ConvertFrom-Json
    Write-Host "  [OK] AWS credentials are configured" -ForegroundColor Green
    Write-Host "  [OK] Connected as: $($callerIdentity.Arn)`n" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] AWS credentials are not configured" -ForegroundColor Red
    Write-Host "`nPlease run: aws configure" -ForegroundColor Yellow
    exit 1
}

# Track what exists and what doesn't
$resources = @{
    OIDCProvider = $false
    GitHubActionsRole = $false
    GitHubActionsPolicy = $false
    ECRRepository = $false
    ECSTaskExecutionRole = $false
    CloudWatchLogGroup = $false
    ECSCluster = $false
}

$missingResources = @()
$existingResources = @()

Write-Host "Checking AWS Resources...`n" -ForegroundColor Cyan

# Check 1: OIDC Provider
Write-Host "[1/7] Checking OIDC Provider for GitHub Actions..." -ForegroundColor Yellow
try {
    $providers = aws iam list-open-id-connect-providers --region $AWSRegion 2>&1 | ConvertFrom-Json
    $oidcProvider = $providers.OpenIDConnectProviderList | Where-Object { $_.Arn -like "*token.actions.githubusercontent.com*" }
    
    if ($oidcProvider) {
        Write-Host "  [EXISTS] OIDC Provider: $($oidcProvider.Arn)" -ForegroundColor Green
        $resources.OIDCProvider = $true
        $existingResources += "OIDC Provider"
    } else {
        Write-Host "  [MISSING] OIDC Provider not found" -ForegroundColor Red
        $missingResources += "OIDC Provider"
    }
} catch {
    Write-Host "  [ERROR] Could not check OIDC Provider" -ForegroundColor Red
    $missingResources += "OIDC Provider"
}

# Check 2: GitHub Actions IAM Role
Write-Host "`n[2/7] Checking IAM Role: github-actions-role..." -ForegroundColor Yellow
try {
    $role = aws iam get-role --role-name github-actions-role --region $AWSRegion 2>&1 | ConvertFrom-Json
    
    if ($role.Role) {
        Write-Host "  [EXISTS] IAM Role: $($role.Role.Arn)" -ForegroundColor Green
        $resources.GitHubActionsRole = $true
        $existingResources += "github-actions-role"
    }
} catch {
    Write-Host "  [MISSING] IAM Role 'github-actions-role' not found" -ForegroundColor Red
    $missingResources += "github-actions-role"
}

# Check 3: GitHub Actions Policy
Write-Host "`n[3/7] Checking IAM Policy: GitHubActionsDeployPolicy..." -ForegroundColor Yellow
try {
    $policies = aws iam list-policies --scope Local --region $AWSRegion 2>&1 | ConvertFrom-Json
    $policy = $policies.Policies | Where-Object { $_.PolicyName -eq "GitHubActionsDeployPolicy" }
    
    if ($policy) {
        Write-Host "  [EXISTS] IAM Policy: $($policy.Arn)" -ForegroundColor Green
        $resources.GitHubActionsPolicy = $true
        $existingResources += "GitHubActionsDeployPolicy"
        
        # Check if attached to role
        if ($resources.GitHubActionsRole) {
            $attachedPolicies = aws iam list-attached-role-policies --role-name github-actions-role --region $AWSRegion 2>&1 | ConvertFrom-Json
            $isAttached = $attachedPolicies.AttachedPolicies | Where-Object { $_.PolicyName -eq "GitHubActionsDeployPolicy" }
            
            if ($isAttached) {
                Write-Host "  [OK] Policy is attached to github-actions-role" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Policy exists but not attached to role" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  [MISSING] IAM Policy 'GitHubActionsDeployPolicy' not found" -ForegroundColor Red
        $missingResources += "GitHubActionsDeployPolicy"
    }
} catch {
    Write-Host "  [MISSING] IAM Policy not found" -ForegroundColor Red
    $missingResources += "GitHubActionsDeployPolicy"
}

# Check 4: ECR Repository
Write-Host "`n[4/7] Checking ECR Repository: $ECRRepoName..." -ForegroundColor Yellow
try {
    $ecr = aws ecr describe-repositories --repository-names $ECRRepoName --region $AWSRegion 2>&1 | ConvertFrom-Json
    
    if ($ecr.repositories) {
        Write-Host "  [EXISTS] ECR Repository: $($ecr.repositories[0].repositoryUri)" -ForegroundColor Green
        $resources.ECRRepository = $true
        $existingResources += "ECR Repository"
    }
} catch {
    Write-Host "  [MISSING] ECR Repository '$ECRRepoName' not found" -ForegroundColor Red
    $missingResources += "ECR Repository"
}

# Check 5: ECS Task Execution Role
Write-Host "`n[5/7] Checking ECS Task Execution Role..." -ForegroundColor Yellow
try {
    $ecsRole = aws iam get-role --role-name ecsTaskExecutionRole --region $AWSRegion 2>&1 | ConvertFrom-Json
    
    if ($ecsRole.Role) {
        Write-Host "  [EXISTS] ECS Task Execution Role: $($ecsRole.Role.Arn)" -ForegroundColor Green
        $resources.ECSTaskExecutionRole = $true
        $existingResources += "ecsTaskExecutionRole"
        
        # Check if policy is attached
        $attachedPolicies = aws iam list-attached-role-policies --role-name ecsTaskExecutionRole --region $AWSRegion 2>&1 | ConvertFrom-Json
        $hasPolicy = $attachedPolicies.AttachedPolicies | Where-Object { $_.PolicyName -eq "AmazonECSTaskExecutionRolePolicy" }
        
        if ($hasPolicy) {
            Write-Host "  [OK] AmazonECSTaskExecutionRolePolicy is attached" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] AmazonECSTaskExecutionRolePolicy not attached" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  [MISSING] ECS Task Execution Role 'ecsTaskExecutionRole' not found" -ForegroundColor Red
    $missingResources += "ecsTaskExecutionRole"
}

# Check 6: CloudWatch Log Group
Write-Host "`n[6/7] Checking CloudWatch Log Group..." -ForegroundColor Yellow
try {
    $logGroups = aws logs describe-log-groups --log-group-name-prefix "/ecs/compliance-platform-staging" --region $AWSRegion 2>&1 | ConvertFrom-Json
    
    if ($logGroups.logGroups.Count -gt 0) {
        Write-Host "  [EXISTS] Log Group: $($logGroups.logGroups[0].logGroupName)" -ForegroundColor Green
        Write-Host "  [OK] Retention: $($logGroups.logGroups[0].retentionInDays) days" -ForegroundColor Green
        $resources.CloudWatchLogGroup = $true
        $existingResources += "CloudWatch Log Group"
    } else {
        Write-Host "  [MISSING] CloudWatch Log Group '/ecs/compliance-platform-staging' not found" -ForegroundColor Red
        $missingResources += "CloudWatch Log Group"
    }
} catch {
    Write-Host "  [MISSING] CloudWatch Log Group not found" -ForegroundColor Red
    $missingResources += "CloudWatch Log Group"
}

# Check 7: ECS Cluster
Write-Host "`n[7/7] Checking ECS Cluster..." -ForegroundColor Yellow
try {
    $cluster = aws ecs describe-clusters --clusters compliance-platform-staging --region $AWSRegion 2>&1 | ConvertFrom-Json
    
    if ($cluster.clusters.Count -gt 0 -and $cluster.clusters[0].status -eq "ACTIVE") {
        Write-Host "  [EXISTS] ECS Cluster: $($cluster.clusters[0].clusterArn)" -ForegroundColor Green
        Write-Host "  [OK] Status: $($cluster.clusters[0].status)" -ForegroundColor Green
        $resources.ECSCluster = $true
        $existingResources += "ECS Cluster"
    } else {
        Write-Host "  [MISSING] ECS Cluster 'compliance-platform-staging' not found" -ForegroundColor Red
        $missingResources += "ECS Cluster"
    }
} catch {
    Write-Host "  [MISSING] ECS Cluster not found" -ForegroundColor Red
    $missingResources += "ECS Cluster"
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$existingCount = $existingResources.Count
$missingCount = $missingResources.Count
$totalCount = $existingCount + $missingCount

Write-Host "Resources Found: $existingCount / $totalCount" -ForegroundColor $(if ($existingCount -eq $totalCount) { "Green" } else { "Yellow" })

if ($existingResources.Count -gt 0) {
    Write-Host "`nExisting Resources:" -ForegroundColor Green
    foreach ($resource in $existingResources) {
        Write-Host "  [OK] $resource" -ForegroundColor Green
    }
}

if ($missingResources.Count -gt 0) {
    Write-Host "`nMissing Resources:" -ForegroundColor Red
    foreach ($resource in $missingResources) {
        Write-Host "  [X] $resource" -ForegroundColor Red
    }
}

# Next Steps
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($missingResources.Count -gt 0) {
    Write-Host "1. Create missing resources by running:" -ForegroundColor Yellow
    Write-Host "   .\scripts\setup-aws-infrastructure.ps1`n" -ForegroundColor Cyan
} else {
    Write-Host "[OK] All AWS resources are created!`n" -ForegroundColor Green
}

Write-Host "2. Configure GitHub Secrets:" -ForegroundColor Yellow
Write-Host "   URL: https://github.com/$GitHubRepo/settings/secrets/actions`n" -ForegroundColor Cyan

Write-Host "   Add these 4 secrets:" -ForegroundColor White
Write-Host "   - AWS_ACCOUNT_ID:  $AWSAccountId" -ForegroundColor Gray
Write-Host "   - AWS_REGION:      $AWSRegion" -ForegroundColor Gray
Write-Host "   - AWS_ROLE_ARN:    arn:aws:iam::${AWSAccountId}:role/github-actions-role" -ForegroundColor Gray
Write-Host "   - ECR_REPOSITORY:  $ECRRepoName`n" -ForegroundColor Gray

if ($resources.ECRRepository) {
    Write-Host "3. Test CI/CD Pipeline:" -ForegroundColor Yellow
    Write-Host "   cd `"c:\Users\user1-baseNaultha\Threat Risk Assessment\compliance-platform-mvp`"" -ForegroundColor Cyan
    Write-Host "   git add ." -ForegroundColor Cyan
    Write-Host "   git commit -m `"Setup CI/CD pipeline`"" -ForegroundColor Cyan
    Write-Host "   git push origin main`n" -ForegroundColor Cyan
    
    Write-Host "4. Monitor workflow at:" -ForegroundColor Yellow
    Write-Host "   https://github.com/$GitHubRepo/actions`n" -ForegroundColor Cyan
}

# Quick command reference
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Quick Commands" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "View ECR images:" -ForegroundColor Yellow
Write-Host "  aws ecr list-images --repository-name $ECRRepoName --region $AWSRegion`n" -ForegroundColor Gray

Write-Host "View ECS cluster:" -ForegroundColor Yellow
Write-Host "  aws ecs describe-clusters --clusters compliance-platform-staging --region $AWSRegion`n" -ForegroundColor Gray

Write-Host "View CloudWatch logs:" -ForegroundColor Yellow
Write-Host "  aws logs tail /ecs/compliance-platform-staging --follow --region $AWSRegion`n" -ForegroundColor Gray

Write-Host ""