#!/bin/bash
# Quick verification script - Tests all Phase 0 components

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Compliance Platform MVP - Phase 0 Verification               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
    fi
}

# 1. Docker Compose
echo "🐳 Docker Compose"
docker-compose ps > /dev/null 2>&1
check "Docker Compose running"

# 2. Database
echo ""
echo "🗄️  Database"
docker-compose exec -T postgres pg_isready -U admin -d multitenantpostgresdb > /dev/null 2>&1
check "PostgreSQL responding"

TABLE_COUNT=$(docker-compose exec -T postgres psql -U admin -d multitenantpostgresdb -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d ' ')
if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Database tables exist ($TABLE_COUNT tables)"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} No database tables found"
    ((FAILED++))
fi

# 3. Backend
echo ""
echo "⚙️  Backend"
docker-compose exec -T backend python -c "from app.main import app; print('OK')" > /dev/null 2>&1
check "FastAPI imports successfully"

docker-compose exec -T backend python -c "from app.models.models import Assessment; print('OK')" > /dev/null 2>&1
check "Models import successfully"

# 4. Health Check
echo ""
echo "💓 Health Check"
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Health endpoint responding"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Health endpoint not responding"
    ((FAILED++))
fi

# 5. Migrations
echo ""
echo "📦 Migrations"
docker-compose exec -T backend alembic current > /dev/null 2>&1
check "Alembic migrations available"

# 6. Configuration
echo ""
echo "⚙️  Configuration"
[ -f ".env.example" ] && echo -e "${GREEN}✓${NC} .env.example exists" && ((PASSED++)) || (echo -e "${RED}✗${NC} .env.example missing" && ((FAILED++)))
[ -f "pyproject.toml" ] && echo -e "${GREEN}✓${NC} pyproject.toml exists" && ((PASSED++)) || (echo -e "${RED}✗${NC} pyproject.toml missing" && ((FAILED++)))
[ -f "backend/pytest.ini" ] && echo -e "${GREEN}✓${NC} pytest.ini configured" && ((PASSED++)) || (echo -e "${RED}✗${NC} pytest.ini missing" && ((FAILED++)))

# 7. GitHub Actions
echo ""
echo "🚀 GitHub Actions"
[ -d ".github/workflows" ] && echo -e "${GREEN}✓${NC} Workflows directory exists" && ((PASSED++)) || (echo -e "${RED}✗${NC} Workflows missing" && ((FAILED++)))
[ -f ".github/workflows/ci.yml" ] && echo -e "${GREEN}✓${NC} CI workflow configured" && ((PASSED++)) || (echo -e "${RED}✗${NC} CI workflow missing" && ((FAILED++)))
[ -f ".github/workflows/deploy.yml" ] && echo -e "${GREEN}✓${NC} Deploy workflow configured" && ((PASSED++)) || (echo -e "${RED}✗${NC} Deploy workflow missing" && ((FAILED++)))
[ -f ".github/workflows/release.yml" ] && echo -e "${GREEN}✓${NC} Release workflow configured" && ((PASSED++)) || (echo -e "${RED}✗${NC} Release workflow missing" && ((FAILED++)))

# 8. Documentation
echo ""
echo "📖 Documentation"
[ -f "docs/TESTING_GUIDE.md" ] && echo -e "${GREEN}✓${NC} Testing guide exists" && ((PASSED++)) || (echo -e "${RED}✗${NC} Testing guide missing" && ((FAILED++)))
[ -f "docs/CICD_PIPELINE.md" ] && echo -e "${GREEN}✓${NC} CI/CD documentation exists" && ((PASSED++)) || (echo -e "${RED}✗${NC} CI/CD documentation missing" && ((FAILED++)))
[ -f ".github/GITHUB_SETUP_GUIDE.md" ] && echo -e "${GREEN}✓${NC} GitHub setup guide exists" && ((PASSED++)) || (echo -e "${RED}✗${NC} GitHub setup guide missing" && ((FAILED++)))

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo -e "║ Results: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC}                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All Phase 0 components verified successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create GitHub repository"
    echo "2. Configure GitHub secrets"
    echo "3. Setup AWS OIDC provider"
    echo "4. Configure branch protection"
    echo "5. Push code to GitHub"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some components need attention${NC}"
    echo ""
    exit 1
fi
