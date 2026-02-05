#!/bin/bash
# Comprehensive test script for Phase 0 MVP

set -e

echo "=========================================="
echo "Compliance Platform MVP - Test Suite"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    echo -e "${YELLOW}TEST: $1${NC}"
}

pass() {
    echo -e "${GREEN}✓ PASSED${NC}"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAILED: $1${NC}"
    ((TESTS_FAILED++))
}

# Test 1: Docker containers running
log_test "Checking if Docker containers are running..."
if docker ps | grep -q "compliance-postgres"; then
    pass
else
    fail "PostgreSQL container not running"
fi

if docker ps | grep -q "compliance-backend"; then
    pass
else
    fail "Backend container not running"
fi

# Test 2: Database connectivity
log_test "Testing database connectivity..."
if docker-compose exec -T postgres pg_isready -U admin -d multitenantpostgresdb > /dev/null 2>&1; then
    pass
else
    fail "Cannot connect to PostgreSQL database"
fi

# Test 3: Health endpoint
log_test "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    pass
else
    fail "Health endpoint returned: $HEALTH_RESPONSE"
fi

# Test 4: Database tables exist
log_test "Checking if database tables were created by migrations..."
TABLE_COUNT=$(docker-compose exec -T postgres psql -U admin -d multitenantpostgresdb -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "  Found $TABLE_COUNT tables"
    pass
else
    fail "No tables found in database"
fi

# Test 5: Specific tables
log_test "Verifying core tables exist..."
REQUIRED_TABLES=("tenants" "users" "assessments" "threats" "evidence" "recommendations" "active_risks" "audit_logs")

for table in "${REQUIRED_TABLES[@]}"; do
    if docker-compose exec -T postgres psql -U admin -d multitenantpostgresdb -t -c "SELECT 1 FROM information_schema.tables WHERE table_name='$table'" | grep -q "1"; then
        echo "  ✓ $table"
    else
        echo "  ✗ $table"
        fail "Table $table not found"
    fi
done

# Test 6: Backend imports
log_test "Testing Python imports..."
if docker-compose exec -T backend python -c "from app.models.models import Assessment, Threat, Evidence; print('OK')" | grep -q "OK"; then
    pass
else
    fail "Python imports failed"
fi

# Test 7: Alembic migrations
log_test "Checking Alembic migration status..."
MIGRATION_STATUS=$(docker-compose exec -T backend alembic current)
if [ -n "$MIGRATION_STATUS" ]; then
    echo "  Current revision: $MIGRATION_STATUS"
    pass
else
    fail "Cannot get migration status"
fi

echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit 1
fi
