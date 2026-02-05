# Phase 0 MVP - Complete Setup & Testing Guide

## ✅ What We've Built

### Project Foundation (Scaffolding)
```
compliance-platform-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application
│   │   ├── core/
│   │   │   ├── config.py            # Configuration management
│   │   │   └── aws.py               # AWS service clients
│   │   ├── db/
│   │   │   ├── database.py          # SQLAlchemy setup
│   │   │   ├── alembic/
│   │   │   │   └── versions/
│   │   │   │       └── 0001_initial.py  # Database migration
│   │   │   └── __init__.py
│   │   ├── models/
│   │   │   ├── models.py            # 9 SQLAlchemy models
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── schemas.py           # 20+ Pydantic schemas
│   │   │   └── __init__.py
│   │   └── utils/
│   │       ├── helpers.py           # Utility functions
│   │       └── __init__.py
│   ├── pyproject.toml               # Dependencies & build config
│   ├── pytest.ini                   # Test configuration ✨ NEW
│   ├── .flake8                      # Linting config ✨ NEW
│   ├── requirements-dev.txt         # Dev dependencies ✨ NEW
│   └── .env.example                 # Configuration template
├── docker/
│   └── Dockerfile                   # Container image
├── docker-compose.yml               # Local dev environment
├── docker-compose.test.yml          # Test environment ✨ NEW
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                   # Lint, test, build ✨ NEW
│   │   ├── deploy.yml               # ECR push, staging deploy ✨ NEW
│   │   └── release.yml              # Production release ✨ NEW
│   ├── GITHUB_SETUP_GUIDE.md        # Setup instructions ✨ NEW
│   └── README.md                    # Workflows overview ✨ NEW
├── scripts/
│   ├── test-setup.sh                # Unix test runner ✨ NEW
│   ├── test-setup.bat               # Windows test runner ✨ NEW
│   ├── setup-cicd.sh                # CICD setup guide ✨ NEW
│   ├── setup-cicd.bat               # CICD setup guide ✨ NEW
│   └── verify-phase0.sh             # Component verification ✨ NEW
├── docs/
│   ├── README.md                    # Project overview
│   ├── QUICK_START.md               # Get started quickly
│   ├── AWS_DATABASE_SETUP.md        # Database configuration
│   ├── TESTING_GUIDE.md             # Testing documentation ✨ NEW
│   └── CICD_PIPELINE.md             # CI/CD architecture ✨ NEW
├── .gitignore
├── CONFIGURATION_SUMMARY.md         # Config reference
└── TESTING_AND_CICD_SETUP.md        # This document ✨ NEW

✨ = Created in this session
```

---

## 🔧 Current Capabilities

### Database
- ✅ 9 SQLAlchemy ORM models
- ✅ Multi-tenant architecture (tenant_id on all tables)
- ✅ Alembic migrations
- ✅ PostgreSQL 15 (local) or Aurora (AWS)
- ✅ Secrets Manager integration for credentials

### Backend
- ✅ FastAPI 0.109.0
- ✅ CORS middleware
- ✅ Health endpoint
- ✅ Configuration management
- ✅ AWS clients (S3, Secrets Manager, Cognito)

### Testing
- ✅ pytest configured
- ✅ Test environment in Docker Compose
- ✅ Coverage reporting
- ✅ Code linting (ruff, black, mypy)
- ✅ Security scanning (bandit)

### CI/CD
- ✅ GitHub Actions workflows (3 files)
- ✅ Automated testing
- ✅ Docker image building
- ✅ ECR push
- ✅ Staging deployment
- ✅ Production release (with approval)

### Documentation
- ✅ Complete testing guide
- ✅ CI/CD architecture documentation
- ✅ GitHub setup instructions
- ✅ AWS database setup guide
- ✅ Quick start guide

---

## 🚀 Quick Start

### 1. Start Local Environment

```bash
# Clone repository
git clone https://github.com/your-org/compliance-platform-mvp.git
cd compliance-platform-mvp

# Start Docker Compose
docker-compose up -d

# Verify services
docker-compose ps

# Run migrations
docker-compose exec backend alembic upgrade head

# Check health
curl http://localhost:8000/health
```

### 2. Verify Setup

```bash
# Run verification script
bash scripts/verify-phase0.sh

# Should see:
# ✓ Docker Compose running
# ✓ PostgreSQL responding
# ✓ Database tables exist (9 tables)
# ✓ FastAPI imports successfully
# ✓ Models import successfully
# ✓ Health endpoint responding
# ✓ Alembic migrations available
# ... (and more)
```

### 3. Run Tests

```bash
# Install test dependencies
pip install -r backend/requirements-dev.txt

# Run all tests
cd backend && pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 4. Setup GitHub

```bash
# Create GitHub repository (manual)
# https://github.com/new

# Configure secrets (manual)
# Settings → Secrets and variables → Actions
# Add: AWS_ACCOUNT_ID, AWS_REGION, AWS_ROLE_ARN, ECR_REPOSITORY

# Push code
git remote add origin https://github.com/your-org/compliance-platform-mvp.git
git push -u origin main

# Monitor CI
# https://github.com/your-org/compliance-platform-mvp/actions
```

---

## 📊 Testing Configuration

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_models.py           # Model tests
├── test_schemas.py          # Schema validation
├── unit/
│   ├── test_services.py
│   └── test_helpers.py
└── integration/
    └── test_database.py
```

### Run Tests

```bash
# All tests
pytest

# Specific test
pytest tests/test_models.py::TestUserModel::test_user_creation

# By marker
pytest -m unit        # Unit tests only
pytest -m integration # Integration tests
pytest -m requires_db # DB tests

# With coverage
pytest --cov=app --cov-report=term-missing

# In parallel
pytest -n auto

# Stop on first failure
pytest -x
```

### Configuration Files

| File | Purpose |
|---|---|
| `backend/pytest.ini` | pytest configuration, markers, coverage settings |
| `backend/.flake8` | Linting rules (isort, black, ruff config) |
| `backend/requirements-dev.txt` | Test dependencies (pytest, moto, bandit, etc.) |
| `docker-compose.test.yml` | Override for test services |

---

## 🔄 CI/CD Pipeline

### Workflows

#### 1. CI Workflow (Continuous Integration)
- **Trigger**: Push or PR to any branch
- **Jobs**: 
  - Lint (ruff, black, mypy) → 2-3 min
  - Test (pytest + coverage) → 5-8 min
  - Security Scan (bandit) → 1-2 min
  - Build (Docker image) → 3-5 min
- **Total Time**: ~15 min

#### 2. Deploy Workflow (Build & Push)
- **Trigger**: Push to main OR manual dispatch
- **Jobs**:
  - Build & Push to ECR → 3-5 min
  - Deploy to Staging → 2-3 min
- **Total Time**: ~8 min

#### 3. Release Workflow (Production)
- **Trigger**: Tag push (v*.*.*)
- **Jobs**:
  - Create Release → 3-5 min
  - Deploy to Production → 2-3 min (requires approval)
- **Total Time**: ~8 min

### Setup AWS

```bash
# 1. Create OIDC Provider
aws iam create-openid-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
  --region ca-central-1

# 2. Create IAM Role (see .github/GITHUB_SETUP_GUIDE.md for trust policy)
# 3. Attach ECR + ECS policies (see GITHUB_SETUP_GUIDE.md)
# 4. Create ECR repository
aws ecr create-repository \
  --repository-name compliance-platform-mvp \
  --region ca-central-1

# 5. Create ECS clusters and services (manual)
```

### GitHub Secrets

```
AWS_ACCOUNT_ID = 031195399879
AWS_REGION = ca-central-1
AWS_ROLE_ARN = arn:aws:iam::031195399879:role/github-actions-role
ECR_REPOSITORY = compliance-platform-mvp
```

---

## 📝 Key Files Reference

### Test & Quality
- `backend/pytest.ini` - Test configuration, markers, coverage
- `backend/.flake8` - Linting configuration
- `backend/requirements-dev.txt` - Development dependencies
- `scripts/test-setup.sh` / `test-setup.bat` - Run tests with validation
- `scripts/verify-phase0.sh` - Verify all Phase 0 components

### GitHub Actions
- `.github/workflows/ci.yml` - Continuous Integration
- `.github/workflows/deploy.yml` - Build & Deploy
- `.github/workflows/release.yml` - Production Release
- `.github/GITHUB_SETUP_GUIDE.md` - Setup instructions

### Documentation
- `docs/TESTING_GUIDE.md` - How to run tests
- `docs/CICD_PIPELINE.md` - CI/CD architecture
- `TESTING_AND_CICD_SETUP.md` - Complete setup guide
- `.github/README.md` - Workflows overview

---

## ✅ Verification Checklist

Before proceeding to Phase 0 API implementation:

### Local Setup
- [ ] Docker Compose starts: `docker-compose up -d` (no errors)
- [ ] Postgres health check passes: `docker-compose ps` (healthy)
- [ ] Migrations run: `docker-compose exec backend alembic upgrade head`
- [ ] Tables created: `docker-compose exec postgres psql -U admin -d multitenantpostgresdb -c "\dt"` (9+ tables)
- [ ] Health endpoint: `curl http://localhost:8000/health` (200 OK)

### Testing
- [ ] Dependencies install: `pip install -r backend/requirements-dev.txt`
- [ ] Pytest discovers tests: `pytest --collect-only`
- [ ] Linting passes: `ruff check backend/app`
- [ ] Format check passes: `black --check backend/app`

### GitHub
- [ ] Repository created
- [ ] Code pushed to main branch
- [ ] Secrets configured
- [ ] GitHub Actions accessible

### AWS
- [ ] OIDC provider created
- [ ] IAM role created
- [ ] IAM policy attached
- [ ] ECR repository created

---

## 🎯 Next Steps (Phase 0 Continuation)

### Immediate
1. ✅ Test local setup (today)
2. ✅ Create GitHub repository (today)
3. ✅ Configure secrets (today)

### Phase 0 API Implementation
1. Create API routers (assessments, threats, evidence, recommendations, risks, admin, auth)
2. Implement service layer (business logic)
3. Implement authentication (Cognito or mock)
4. Create integration tests
5. Create React frontend skeleton

### Phase 1 (Deferred)
- Textract integration for document processing
- Bedrock/SageMaker AI models for threat analysis
- Step Functions for complex workflows
- OpenSearch for advanced filtering

---

## 🐛 Troubleshooting

### Docker Issues
```bash
# Container won't start
docker-compose logs postgres
docker-compose logs backend

# Rebuild containers
docker-compose down -v
docker-compose up -d

# Check disk space
docker system df
docker system prune -a
```

### Database Issues
```bash
# Connection refused
docker-compose exec postgres pg_isready -U admin -d multitenantpostgresdb

# Migrations failed
docker-compose exec backend alembic history
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head

# Check tables
docker-compose exec postgres psql -U admin -d multitenantpostgresdb -c "\dt"
```

### Test Issues
```bash
# Import errors
export PYTHONPATH=$PWD:$PYTHONPATH
pytest tests/test_models.py -vv

# Connection errors
docker-compose ps
docker-compose logs postgres

# Cleanup and retry
rm -rf backend/.pytest_cache backend/__pycache__
pytest -v
```

### CI/CD Issues
```bash
# View workflow logs
gh run list
gh run view <RUN_ID> --log

# Check secrets
gh secret list

# Re-run workflow
gh run rerun <RUN_ID>
```

---

## 📚 Documentation Map

| Document | Purpose |
|---|---|
| [QUICK_START.md](docs/QUICK_START.md) | Get up and running (5 min) |
| [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | How to run tests and coverage |
| [CICD_PIPELINE.md](docs/CICD_PIPELINE.md) | CI/CD workflows and architecture |
| [AWS_DATABASE_SETUP.md](docs/AWS_DATABASE_SETUP.md) | Database configuration and Secrets Manager |
| [.github/GITHUB_SETUP_GUIDE.md](.github/GITHUB_SETUP_GUIDE.md) | Complete GitHub + AWS setup |
| [CONFIGURATION_SUMMARY.md](CONFIGURATION_SUMMARY.md) | Configuration quick reference |
| [README.md](README.md) | Project overview |

---

## 🎓 Learning Resources

### FastAPI
- [Official Documentation](https://fastapi.tiangolo.com)
- [Advanced Features](https://fastapi.tiangolo.com/advanced/)
- [Deployment Guide](https://fastapi.tiangolo.com/deployment/)

### SQLAlchemy
- [Official Documentation](https://docs.sqlalchemy.org/)
- [ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)

### pytest
- [Official Documentation](https://docs.pytest.org/)
- [Fixtures Guide](https://docs.pytest.org/en/7.1.x/fixture.html)

### GitHub Actions
- [Official Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

### AWS
- [ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)

---

## 📞 Support

For issues or questions:

1. **Check Documentation**
   - See relevant guide in `/docs` or `.github`
   - Check troubleshooting sections

2. **Review Logs**
   - Docker: `docker-compose logs service_name`
   - GitHub Actions: View workflow run logs
   - Application: Check stdout/stderr

3. **Verify Environment**
   - Run `scripts/verify-phase0.sh`
   - Check Docker services: `docker-compose ps`
   - Check configuration: `cat .env.example`

---

## 🎉 Summary

**What's Ready**:
- ✅ Complete project structure
- ✅ Database models and migrations
- ✅ FastAPI backend scaffold
- ✅ Docker development environment
- ✅ Testing infrastructure
- ✅ CI/CD pipelines
- ✅ Comprehensive documentation

**What's Next**:
- ⏳ API routers and services
- ⏳ Authentication integration
- ⏳ React frontend
- ⏳ Integration tests
- ⏳ Production deployment

---

**Status**: ✅ Phase 0 Scaffolding Complete - Ready for API Implementation

**Created**: 2024
**Version**: Phase 0 Testing & CI/CD Setup (Session 18)
**Architecture**: FastAPI + PostgreSQL + Docker + GitHub Actions + AWS (ECR, ECS, Secrets Manager)
