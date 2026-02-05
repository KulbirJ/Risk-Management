# Testing Guide

This guide covers running tests locally and in CI/CD environments.

## Table of Contents

1. [Local Testing](#local-testing)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Coverage Reports](#coverage-reports)
6. [Troubleshooting](#troubleshooting)

## Local Testing

### Prerequisites

```bash
# Install test dependencies
pip install -r backend/requirements-dev.txt

# Includes: pytest, pytest-cov, pytest-asyncio, moto, black, ruff, mypy
```

### Setup Test Environment

```bash
# Create test .env file
cat > backend/.env.test <<EOF
DEBUG=True
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://admin:admin_password@localhost:5432/multitenantpostgresdb
USE_SECRETS_MANAGER=False
AWS_REGION=ca-central-1
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=test-secret-key-only-for-testing
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
EOF
```

### Start Test Environment

```bash
# Using Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d

# Wait for services to be healthy
docker-compose exec postgres pg_isready -U admin -d multitenantpostgresdb
docker-compose exec redis redis-cli ping

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Run Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestUserModel

# Run specific test function
pytest tests/test_models.py::TestUserModel::test_user_creation

# Run tests matching a pattern
pytest -k "test_user" -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing --cov-report=html

# Run tests in parallel (faster)
pytest -n auto

# Run with verbose output
pytest -vv

# Run with print statements shown
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

## Unit Tests

Unit tests cover individual functions and classes in isolation using mocked dependencies.

### Example Unit Test

```python
# tests/test_models.py
import pytest
from app.models.models import User, Tenant
from app.schemas.schemas import UserCreate

@pytest.mark.unit
def test_create_user(db_session):
    """Test user creation with valid data."""
    user = User(
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        roles=["assessor"]
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.email == "test@example.com"
    assert "assessor" in user.roles
```

### Running Unit Tests Only

```bash
pytest -m unit -v
```

## Integration Tests

Integration tests verify that components work together correctly with actual services (Postgres, Redis).

### Example Integration Test

```python
# tests/integration/test_assessment_service.py
import pytest
from app.services.assessment_service import AssessmentService
from app.schemas.schemas import AssessmentCreate

@pytest.mark.integration
@pytest.mark.requires_db
async def test_create_assessment(db_session, tenant_id):
    """Test assessment creation through service layer."""
    service = AssessmentService(db_session)
    
    assessment_data = AssessmentCreate(
        name="Test Assessment",
        description="Test",
        scope="Test scope"
    )
    
    assessment = await service.create_assessment(tenant_id, assessment_data)
    
    assert assessment.id is not None
    assert assessment.name == "Test Assessment"
```

### Running Integration Tests

```bash
pytest -m integration -v
pytest -m requires_db -v
```

## CI/CD Pipeline

### GitHub Actions Workflows

The CI/CD pipeline runs automatically on:
- **Push to main/develop branches**
- **Pull requests**
- **Manual triggers**

### Workflow: Continuous Integration (ci.yml)

```yaml
Jobs:
1. Lint - Code quality checks
   - Ruff linter
   - Black formatting check
   - mypy type checking

2. Test - Unit and integration tests
   - pytest with coverage
   - Services: PostgreSQL, Redis
   
3. Security Scan - Bandit security analysis

4. Build - Docker image build
```

### Viewing CI/CD Results

```bash
# Using GitHub CLI
gh workflow list
gh workflow run ci.yml
gh run list
gh run view <RUN_ID>

# Or view in browser
# https://github.com/{owner}/{repo}/actions
```

## Coverage Reports

### Generate Coverage Locally

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

### Coverage Requirements

- **Minimum**: 70% code coverage
- **Target**: 85% code coverage
- **Critical paths**: 95% coverage (auth, data models, risk scoring)

### Exclude from Coverage

```python
# In code, mark lines to exclude from coverage
if TYPE_CHECKING:  # pragma: no cover
    pass

# Or use coverage comment
x = debug_function()  # pragma: no cover
```

## Performance Testing

### Stress Testing Local API

```bash
# Install locust
pip install locust

# Create locustfile.py and run
locust -f locustfile.py --host=http://localhost:8000
```

### Database Query Performance

```bash
# Check slow queries
docker-compose exec postgres psql -U admin -d multitenantpostgresdb -c \
  "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

## Troubleshooting

### Common Issues

#### 1. "No module named 'app'"

```bash
# Solution: Make sure you're in the backend directory
cd backend
export PYTHONPATH=$PWD:$PYTHONPATH
pytest
```

#### 2. "Connection refused: 5432"

```bash
# Solution: Start Docker Compose first
docker-compose up -d postgres redis
docker-compose exec postgres pg_isready -U admin -d multitenantpostgresdb
```

#### 3. "Database does not exist"

```bash
# Solution: Run migrations
docker-compose exec backend alembic upgrade head
```

#### 4. "Test collection failed"

```bash
# Solution: Check pytest configuration
pytest --version
cat backend/pytest.ini
```

#### 5. "Permission denied" errors

```bash
# Solution: Fix permissions
chmod +x scripts/test-setup.sh
chmod +x scripts/test-setup.bat
```

### Debugging Tests

```bash
# Run with verbose output and print statements
pytest -vv -s

# Run with debugger breakpoint
pytest --pdb  # Drops into debugger on failure

# Run single test with debugger
pytest tests/test_file.py::test_function -vv -s --pdb

# Show all print statements
pytest -s
```

### Clean Up

```bash
# Stop Docker services
docker-compose down

# Remove test database
docker volume rm compliance-platform-mvp_postgres_data_test

# Remove test cache
rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage

# Restart clean
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## CI/CD Secrets & Variables

### GitHub Repository Secrets (Set in Settings)

```
AWS_ACCOUNT_ID=031195399879
AWS_REGION=ca-central-1
AWS_ROLE_ARN=arn:aws:iam::031195399879:role/github-actions-role
ECR_REPOSITORY=compliance-platform-mvp
```

### Test Environment Variables

Set in `.env.test` or in CI workflow:

```
DEBUG=False
LOG_LEVEL=INFO
DATABASE_URL=postgresql://admin:admin_password@localhost:5432/multitenantpostgresdb
USE_SECRETS_MANAGER=False
JWT_SECRET_KEY=test-secret-key-for-testing-only
```

## Next Steps

1. Run local tests: `pytest -v`
2. Check coverage: `pytest --cov=app --cov-report=html`
3. Push to GitHub to trigger CI
4. Monitor workflow results in Actions tab
5. Merge only when all checks pass

For more information, see:
- [GITHUB_SETUP_GUIDE.md](.github/GITHUB_SETUP_GUIDE.md)
- [pytest documentation](https://docs.pytest.org/)
- [GitHub Actions documentation](https://docs.github.com/en/actions)
