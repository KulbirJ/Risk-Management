#!/bin/bash
# Setup script for GitHub Actions environment

set -e

echo "=== Setting up CI/CD Environment ==="

# Variables
REPO_URL="https://github.com/your-org/compliance-platform-mvp.git"
AWS_ACCOUNT_ID="031195399879"
AWS_REGION="ca-central-1"
ECR_REPOSITORY="compliance-platform-mvp"
GITHUB_ORG="your-org"
GITHUB_REPO="compliance-platform-mvp"

echo ""
echo "1. Creating GitHub repository..."
echo "   Repository: $GITHUB_ORG/$GITHUB_REPO"
echo "   URL: $REPO_URL"
echo ""

echo "2. GitHub Secrets to configure:"
echo "   - AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
echo "   - AWS_REGION: $AWS_REGION"
echo "   - AWS_ROLE_ARN: arn:aws:iam::$AWS_ACCOUNT_ID:role/github-actions-role"
echo "   - ECR_REPOSITORY: $ECR_REPOSITORY"
echo ""

echo "3. AWS Setup:"
echo "   a) Create OIDC Provider:"
echo "      aws iam create-openid-connect-provider \\"
echo "        --url 'https://token.actions.githubusercontent.com' \\"
echo "        --client-id-list 'sts.amazonaws.com' \\"
echo "        --thumbprint-list '6938fd4d98bab03faadb97b34396831e3780aea1' \\"
echo "        --region $AWS_REGION"
echo ""
echo "   b) Create IAM Role:"
echo "      See .github/GITHUB_SETUP_GUIDE.md for trust policy"
echo ""
echo "   c) Create IAM Policy:"
echo "      See .github/GITHUB_SETUP_GUIDE.md for policy JSON"
echo ""

echo "4. ECR Repository:"
echo "   aws ecr create-repository \\"
echo "     --repository-name $ECR_REPOSITORY \\"
echo "     --region $AWS_REGION"
echo ""

echo "5. GitHub Branch Protection:"
echo "   https://github.com/$GITHUB_ORG/$GITHUB_REPO/settings/branches"
echo "   Configure main and develop branches"
echo ""

echo "6. Deploy to GitHub:"
echo "   git remote add origin $REPO_URL"
echo "   git push -u origin main"
echo ""

echo "=== Setup Complete ==="
echo ""
echo "For detailed instructions, see:"
echo "  - .github/GITHUB_SETUP_GUIDE.md"
echo "  - docs/CICD_PIPELINE.md"
echo "  - docs/TESTING_GUIDE.md"
