# GitHub Repository Configuration Guide

## Setup Instructions

### 1. Create GitHub Repository

```bash
git remote add origin https://github.com/your-org/compliance-platform-mvp.git
git branch -M main
git push -u origin main
```

### 2. Configure Secrets

Go to: **Settings → Secrets and variables → Actions**

Add the following secrets:

#### AWS Credentials

| Secret Name | Value | Description |
|---|---|---|
| `AWS_ACCOUNT_ID` | `031195399879` | AWS Account ID |
| `AWS_REGION` | `ca-central-1` | AWS Region |
| `AWS_ROLE_ARN` | `arn:aws:iam::031195399879:role/github-actions-role` | IAM Role for GitHub Actions |

#### ECR Configuration

| Secret Name | Value | Description |
|---|---|---|
| `ECR_REPOSITORY` | `compliance-platform-mvp` | ECR repository name |

#### Database Secrets (Production Deployment)

| Secret Name | Value | Description |
|---|---|---|
| `DB_SECRET_NAME` | `compliance-platform/db/credentials` | AWS Secrets Manager secret name |
| `RDS_CLUSTER_IDENTIFIER` | `compliance-platform-prod` | RDS Cluster ID |

### 3. Configure Branch Protection Rules

#### Main Branch (`main`)

Go to: **Settings → Branches → Add rule**

**Branch name pattern**: `main`

- ✅ Require status checks to pass before merging
  - Required status checks:
    - `ci / lint`
    - `ci / test`
    - `ci / build`
    - `security-scan`
- ✅ Require code reviews before merging (1+ reviewers)
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require branches to be up to date before merging
- ✅ Restrict who can push to matching branches (Admins only)

#### Develop Branch (`develop`)

**Branch name pattern**: `develop`

- ✅ Require status checks to pass before merging
  - Required status checks:
    - `ci / lint`
    - `ci / test`
    - `ci / build`
- ✅ Require code reviews before merging (1+ reviewers)
- ✅ Allow auto-merge (SQUASH)

### 4. Configure CI/CD Variables

Go to: **Settings → Secrets and variables → Variables**

| Variable Name | Value |
|---|---|
| `DOCKER_REGISTRY` | `${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.ca-central-1.amazonaws.com` |
| `ECR_REPOSITORY` | `compliance-platform-mvp` |
| `STAGING_CLUSTER` | `compliance-platform-staging` |
| `PRODUCTION_CLUSTER` | `compliance-platform-production` |
| `STAGING_SERVICE` | `compliance-platform-staging` |
| `PRODUCTION_SERVICE` | `compliance-platform-production` |

### 5. Set Up AWS IAM Role for GitHub Actions

Create IAM role `github-actions-role` with trust relationship:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::031195399879:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:your-org/compliance-platform-mvp:*"
        }
      }
    }
  ]
}
```

Attach policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "arn:aws:ecr:ca-central-1:031195399879:repository/compliance-platform-mvp"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:ListServices",
        "ecs:UpdateService",
        "ecs:RegisterTaskDefinition"
      ],
      "Resource": "*"
    }
  ]
}
```

### 6. Configure PR Settings

Go to: **Settings → General → Pull Requests**

- ✅ Allow auto-merge
- ✅ Allow squash merging (recommended)
- ✅ Automatically delete head branches

### 7. Configure Actions Permissions

Go to: **Settings → Actions → General**

- ✅ Allow GitHub Actions to create and approve pull requests
- ✅ Require approval for first-time contributors

## Workflows Overview

### 1. CI Workflow (`ci.yml`)

**Triggers**: Push to `main`, `develop`, `feature/*`; Pull requests

**Jobs**:
- **Lint**: Ruff, Black, mypy
- **Test**: pytest with coverage (services: Postgres, Redis)
- **Security Scan**: Bandit
- **Build**: Docker image build

### 2. Deploy Workflow (`deploy.yml`)

**Triggers**: Push to `main`; Manual workflow dispatch

**Jobs**:
- **Build and Push**: Build Docker image, push to ECR
- **Deploy Staging**: Deploy to ECS staging environment

### 3. Release Workflow (`release.yml`)

**Triggers**: Tag push (`v*.*.*`)

**Jobs**:
- **Release**: Build Docker image, create GitHub Release
- **Deploy Production**: Deploy to ECS production (requires manual approval)

## Local GitHub CLI Setup (Optional)

```bash
# Authenticate
gh auth login

# Clone repository
gh repo clone your-org/compliance-platform-mvp

# Create feature branch
gh checkout -b feature/my-feature

# Create pull request
gh pr create --title "My Feature" --body "Description"

# Check PR status
gh pr status
```

## Troubleshooting

### Workflow Fails with "No secrets available"

- Check that secrets are configured in Settings → Secrets
- Verify secret names match exactly in workflow YAML
- Ensure runner has access (public/private repo settings)

### ECR Push Fails

- Verify AWS_ACCOUNT_ID and AWS_REGION are correct
- Check IAM role has ECR permissions
- Ensure ECR repository exists: `aws ecr describe-repositories --repository-names compliance-platform-mvp --region ca-central-1`

### ECS Deployment Fails

- Verify ECS cluster and service exist
- Check task definition JSON is valid
- Ensure IAM role has ECS permissions

## Next Steps

1. Push code to GitHub: `git push -u origin main`
2. Configure secrets in GitHub Settings
3. Set up branch protection rules
4. Create IAM role in AWS
5. Run workflows to verify CI/CD pipeline
