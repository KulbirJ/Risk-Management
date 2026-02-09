# CI/CD Pipeline Documentation

## Overview

The compliance platform uses GitHub Actions to automate testing, building, and deployment.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    ┌────────┐        ┌────────┐        ┌──────────┐
    │ Push   │        │ Pull   │        │   Tag    │
    │ to     │        │Request │        │ Push     │
    │Main   │        │        │        │(v*.*.*)  │
    └────────┘        └────────┘        └──────────┘
        │                  │                  │
        ▼                  ▼                  ▼
    ┌────────┐        ┌────────┐        ┌──────────┐
    │   CI   │        │   CI   │        │ Release  │
    │Lint→   │        │Lint→   │        │Lint→     │
    │Test→   │        │Test→   │        │Test→     │
    │Build   │        │Build   │        │Build     │
        │                  │                  │
        ▼                  ▼                  ▼
    ┌────────┐        ┌────────┐        ┌──────────┐
    │  ECR   │        │  ✗ or  │        │   ECR    │
    │ Push   │        │ ✓ Merge│        │ Push     │
    │ →      │        │        │        │ Release  │
    │Deploy  │        │        │        │ →Staging │
    │Staging │        │        │        │          │
    └────────┘        └────────┘        └──────────┘
        │                               │
        ▼                               ▼
    Staging                        ┌──────────┐
    Environment                    │Approval  │
                                   │Required  │
                                   └──────────┘
                                       │
                                       ▼
                                  Production
                                  Environment
```

## Workflows

### 1. Continuous Integration (`ci.yml`)

**Trigger**: Push or Pull Request to any branch

**Jobs**:

#### Job: Lint
- **Step 1**: Checkout code
- **Step 2**: Setup Python 3.11 with pip cache
- **Step 3**: Install dependencies (FastAPI, SQLAlchemy, testing tools)
- **Step 4**: Run Ruff linter (code quality)
- **Step 5**: Check Black formatting
- **Step 6**: Run mypy type checking

**Artifacts**: None (just validation)

#### Job: Test
- **Step 1**: Checkout code
- **Step 2**: Setup Python 3.11
- **Step 3**: Start services (PostgreSQL 15, Redis 7)
- **Step 4**: Install dependencies + pytest
- **Step 5**: Create test .env file
- **Step 6**: Wait for PostgreSQL
- **Step 7**: Run Alembic migrations (`alembic upgrade head`)
- **Step 8**: Execute pytest with coverage
- **Step 9**: Upload coverage to Codecov

**Services**:
- PostgreSQL 15-alpine (port 5432)
- Redis 7-alpine (port 6379)

**Artifacts**: 
- Coverage reports
- Test results

#### Job: Security Scan
- **Step 1**: Checkout code
- **Step 2**: Setup Python 3.11
- **Step 3**: Install Bandit security analyzer
- **Step 4**: Run Bandit scan (SAST)
- **Step 5**: Upload report

**Artifacts**: 
- `bandit-report.json`

#### Job: Build
- **Step 1**: Checkout code
- **Step 2**: Setup Docker Buildx
- **Step 3**: Build Docker image
- **Step 4**: Tag image: `compliance-platform-mvp:sha`

**Artifacts**: Docker image (local only)

---

### 2. Build & Deploy (`deploy.yml`)

**Trigger**: Push to `main` branch OR manual dispatch

**Jobs**:

#### Job: Build and Push
- **Step 1**: Checkout code
- **Step 2**: Configure AWS credentials (OIDC)
- **Step 3**: Login to ECR
- **Step 4**: Build and push to ECR
  - Tag: `compliance-platform-mvp:sha`
  - Also tag as `latest` on main branch
- **Step 5**: Create deployment artifact
- **Step 6**: Upload artifact

**AWS Actions Used**:
- `aws-actions/configure-aws-credentials@v2` (OIDC)
- `aws-actions/amazon-ecr-login@v1`

**Artifacts**:
- `image-definitions.json` (ECR image URI)

#### Job: Deploy Staging
- **Dependency**: `build-and-push` (waits to complete)
- **Condition**: Only on `main` branch pushes
- **Step 1**: Checkout code
- **Step 2**: Configure AWS credentials
- **Step 3**: Download deployment artifact
- **Step 4**: Render ECS task definition
  - Updates image URI in `infrastructure/ecs/task-definition-staging.json`
- **Step 5**: Deploy to ECS
  - Cluster: `compliance-platform-staging`
  - Service: `compliance-platform-staging`
- **Step 6**: Create GitHub Deployment record

**AWS Actions Used**:
- `aws-actions/amazon-ecs-render-task-definition@v1`
- `aws-actions/amazon-ecs-deploy-task-definition@v1`

---

### 3. Release (`release.yml`)

**Trigger**: Push tag matching `v*.*.*` (e.g., `v1.0.0`)

**Jobs**:

#### Job: Release
- **Step 1**: Checkout code
- **Step 2**: Extract version from tag
- **Step 3**: Configure AWS credentials
- **Step 4**: Login to ECR
- **Step 5**: Build and push with version tag
  - Tag: `compliance-platform-mvp:v1.0.0`
  - Also: `compliance-platform-mvp:latest`
- **Step 6**: Create GitHub Release
  - Includes version, commit info, docker pull command

**Artifacts**: GitHub Release

#### Job: Deploy Production
- **Dependency**: `release` (waits to complete)
- **Environment**: `production` (requires approval in GitHub)
- **Step 1**: Checkout code
- **Step 2**: Extract version from tag
- **Step 3**: Configure AWS credentials
- **Step 4**: Render ECS task definition (production)
- **Step 5**: Deploy to ECS
  - Cluster: `compliance-platform-production`
  - Service: `compliance-platform-production`
- **Step 6**: Create GitHub Production Deployment

---

## Configuration Requirements

### GitHub Secrets (Settings → Secrets)

```
AWS_ACCOUNT_ID = 031195399879
AWS_REGION = ca-central-1
AWS_ROLE_ARN = arn:aws:iam::031195399879:role/github-actions-role
ECR_REPOSITORY = compliance-platform-mvp
```

### AWS Setup

#### OIDC Provider Configuration

```bash
# Create OIDC provider in AWS
aws iam create-openid-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"
```

#### IAM Role for GitHub Actions

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

#### IAM Policy (ECR + ECS)

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
        "ecs:UpdateService",
        "ecs:RegisterTaskDefinition"
      ],
      "Resource": "*"
    }
  ]
}
```

### AWS ECS Prerequisites

#### Staging Environment
- **Cluster**: `compliance-platform-staging`
- **Service**: `compliance-platform-staging`
- **Task Definition**: `infrastructure/ecs/task-definition-staging.json`

#### Production Environment
- **Cluster**: `compliance-platform-production`
- **Service**: `compliance-platform-production`
- **Task Definition**: `infrastructure/ecs/task-definition-production.json`

#### ECR Repository
- **Repository Name**: `compliance-platform-mvp`
- **Region**: `ca-central-1`

---

## Workflow Execution Details

### CI Workflow Execution Times

| Job | Duration | Services |
|---|---|---|
| Lint | 2-3 min | Python setup only |
| Test | 5-8 min | Python + Postgres + Redis |
| Security | 1-2 min | Python only |
| Build | 3-5 min | Docker |
| **Total** | **~15 min** | All parallel where possible |

### Deploy Workflow Times

| Job | Duration | Notes |
|---|---|---|
| Build & Push | 3-5 min | ECR push time varies |
| Deploy Staging | 2-3 min | ECS update + health checks |
| **Total** | **~8 min** | Sequential |

### Release Workflow Times

| Job | Duration | Notes |
|---|---|---|
| Release (build + release) | 3-5 min | Creates GitHub Release |
| Deploy Production | 2-3 min | Requires manual approval |
| **Total** | **~8 min** | (excluding approval wait) |

---

## Branch Protection Rules

### Main Branch

```yaml
Required Status Checks:
  - ci / lint
  - ci / test
  - ci / build
  - security-scan

Require Pull Request Reviews: Yes (1+ reviewers)
Dismiss Stale Reviews: Yes
Require Status Checks: Yes
Require Branches Up to Date: Yes
Admins Can Push: No
```

### Develop Branch

```yaml
Required Status Checks:
  - ci / lint
  - ci / test
  - ci / build

Require Pull Request Reviews: Yes (1+ reviewers)
Allow Auto-Merge: Yes (squash)
```

---

## Monitoring & Troubleshooting

### View Workflow Runs

```bash
# List all workflows
gh workflow list

# Watch a specific workflow
gh run watch <RUN_ID>

# View run logs
gh run view <RUN_ID> --log

# View job logs
gh run view <RUN_ID> --log-failed
```

### Common Issues

#### 1. "Permission Denied: ECR Push"

**Cause**: AWS credentials not configured or IAM policy missing
**Solution**: 
- Verify AWS_ROLE_ARN secret
- Check IAM policy has ECR permissions
- Verify ECR repository exists

#### 2. "Database Connection Failed"

**Cause**: PostgreSQL health check timeout
**Solution**:
- Increase health check retries
- Check Docker image availability
- Verify network connectivity

#### 3. "ECS Deployment Failed"

**Cause**: Task definition or service doesn't exist
**Solution**:
- Create ECS cluster and service first
- Verify task definition JSON is valid
- Check IAM role has ECS permissions

#### 4. "Test Coverage Below Threshold"

**Cause**: New code without tests
**Solution**:
- Add unit/integration tests
- Update coverage threshold if needed
- Use coverage.py for coverage analysis

---

## Best Practices

1. **Always test locally first**
   ```bash
   docker-compose up -d
   pytest -v
   ```

2. **Keep test dependencies minimal**
   - Use mocks for external services
   - Use ephemeral databases for integration tests

3. **Monitor CI/CD performance**
   - Parallel jobs where possible
   - Cache dependencies
   - Use Docker layer caching

4. **Secure secrets properly**
   - Use GitHub Actions secrets
   - Rotate credentials regularly
   - Never commit secrets to repo

5. **Document deployment procedures**
   - Keep infrastructure templates up to date
   - Document manual approval steps
   - Maintain runbooks for incidents

---

## Next Steps

1. Create GitHub repository
2. Configure GitHub secrets
3. Set up AWS OIDC provider
4. Create IAM role and policy
5. Create ECS clusters and services
6. Push code to trigger CI/CD
7. Monitor workflows and fix any issues
8. Deploy to production with approval

For detailed setup instructions, see [GITHUB_SETUP_GUIDE.md](.github/GITHUB_SETUP_GUIDE.md).
