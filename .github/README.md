# Compliance Platform MVP - CI/CD Pipeline

This directory contains GitHub Actions workflows for automated testing, building, and deployment.

## Workflows

### 1. **ci.yml** - Continuous Integration
- Runs on: Push to main/develop/feature branches and PRs
- Jobs:
  - **Lint**: Code quality checks (Ruff, Black, mypy)
  - **Test**: Unit tests with pytest and coverage
  - **Security Scan**: Bandit security analysis
  - **Build**: Docker image build

### 2. **deploy.yml** - Build & ECR Push
- Runs on: Push to main branch or manual trigger
- Jobs:
  - **Build and Push**: Creates Docker image and pushes to AWS ECR
  - **Deploy Staging**: Deploys to staging ECS cluster

### 3. **release.yml** - Production Release
- Runs on: Git tag (v*.*.*)
- Jobs:
  - **Release**: Creates GitHub Release and pushes to ECR
  - **Deploy Production**: Deploys to production (requires approval)

## Quick Start

### 1. Setup GitHub Repository Secrets

```bash
# AWS Credentials
gh secret set AWS_ACCOUNT_ID --body "031195399879"
gh secret set AWS_REGION --body "ca-central-1"
gh secret set AWS_ROLE_ARN --body "arn:aws:iam::031195399879:role/github-actions-role"

# ECR
gh secret set ECR_REPOSITORY --body "compliance-platform-mvp"
```

### 2. Enable Branch Protection

```bash
# For main branch
gh api repos/{owner}/{repo}/branches/main/protection \
  -f required_status_checks='{"strict": true, "contexts": ["ci/lint", "ci/test", "ci/build"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count": 1}'
```

### 3. Push and Test

```bash
git push origin main
# View workflow runs: https://github.com/{owner}/{repo}/actions
```

## Workflow Files

- `ci.yml` - Lint, test, build
- `deploy.yml` - ECR push and staging deployment
- `release.yml` - Production release and deployment

See [GITHUB_SETUP_GUIDE.md](GITHUB_SETUP_GUIDE.md) for detailed configuration.
