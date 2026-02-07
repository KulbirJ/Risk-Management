@echo off
REM Setup script for GitHub Actions environment (Windows)

echo.
echo === Setting up CI/CD Environment ===
echo.

set REPO_URL=https://github.com/your-org/compliance-platform-mvp.git
set AWS_ACCOUNT_ID=031195399879
set AWS_REGION=ca-west-1
set ECR_REPOSITORY=compliance-platform-mvp
set GITHUB_ORG=your-org
set GITHUB_REPO=compliance-platform-mvp

echo 1. Creating GitHub repository...
echo    Repository: %GITHUB_ORG%/%GITHUB_REPO%
echo    URL: %REPO_URL%
echo.

echo 2. GitHub Secrets to configure:
echo    - AWS_ACCOUNT_ID: %AWS_ACCOUNT_ID%
echo    - AWS_REGION: %AWS_REGION%
echo    - AWS_ROLE_ARN: arn:aws:iam::%AWS_ACCOUNT_ID%:role/github-actions-role
echo    - ECR_REPOSITORY: %ECR_REPOSITORY%
echo.

echo 3. AWS Setup:
echo    a) Create OIDC Provider - See .github/GITHUB_SETUP_GUIDE.md
echo    b) Create IAM Role - See .github/GITHUB_SETUP_GUIDE.md
echo    c) Create IAM Policy - See .github/GITHUB_SETUP_GUIDE.md
echo.

echo 4. ECR Repository:
echo    aws ecr create-repository ^
echo      --repository-name %ECR_REPOSITORY% ^
echo      --region %AWS_REGION%
echo.

echo 5. GitHub Branch Protection:
echo    https://github.com/%GITHUB_ORG%/%GITHUB_REPO%/settings/branches
echo.

echo 6. Deploy to GitHub:
echo    git remote add origin %REPO_URL%
echo    git push -u origin main
echo.

echo === Setup Complete ===
echo.
echo For detailed instructions, see:
echo   - .github/GITHUB_SETUP_GUIDE.md
echo   - docs/CICD_PIPELINE.md
echo   - docs/TESTING_GUIDE.md
echo.
