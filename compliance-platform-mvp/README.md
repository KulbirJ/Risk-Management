# Compliance Platform MVP - Phase 0

Cybersecurity Risk Assessment Compliance Platform (AWS + FastAPI + React SPA)

## Overview

**Phase 0**: Core MVP for risk assessments without AI components.
- Assessment CRUD and threat management
- Manual threat entry with static catalogue lookups
- Evidence upload to AWS S3 (presigned URLs)
- Rule-based likelihood and impact scoring
- Active Risk Register for non-remediable threats
- User authentication (Cognito) and RBAC
- Comprehensive audit logging
- FastAPI backend + React SPA frontend

**Phase 1** (future): AI/intelligence components (Textract, Bedrock, LLM enrichment)

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, Pydantic
- **Frontend**: React, Vite, Axios
- **Database**: PostgreSQL (Aurora Serverless v2 in AWS; local Postgres in dev)
- **Cloud**: AWS (S3, Cognito, Secrets Manager, KMS, CloudWatch)
- **DevOps**: Docker, Docker Compose, Terraform
- **Region**: ca-central-1 (Canada)

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- AWS CLI v2 configured with ca-central-1
- AWS Account with ID: 031195399879
- Node.js 18+ (for frontend development)

## Local Development Setup

### 1. Clone and Environment Setup

```bash
cd c:\Users\user1-baseNaultha\Threat Risk Assessment\compliance-platform-mvp
cp .env.example .env
```

Edit `.env` with your local values (Cognito details, S3 bucket name, etc.)

### 2. Start Docker Compose (Postgres + Redis + Backend)

```bash
docker-compose up --build
```

This starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- FastAPI backend on `http://localhost:8000`

### 3. Run Database Migrations

In a new terminal:

```bash
docker-compose exec backend alembic upgrade head
```

### 4. Verify Setup

Access FastAPI Swagger UI:

```
http://localhost:8000/docs
```

Check health endpoint:

```bash
curl http://localhost:8000/health
```

### 5. Frontend Development (Phase 0)

In `frontend/` folder:

```bash
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

## Backend Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app factory
│   ├── api/
│   │   ├── assessments.py        # Assessment CRUD routes (Phase 0)
│   │   ├── threats.py            # Threat management routes
│   │   ├── evidence.py           # Evidence upload routes
│   │   ├── auth.py               # Authentication/login routes
│   │   ├── admin.py              # Audit log & admin routes
│   │   └── intelligence.py       # Placeholder for Phase 1 AI routes
│   ├── core/
│   │   ├── config.py             # Settings from environment
│   │   ├── security.py           # JWT/Cognito helpers (Phase 0)
│   │   └── aws.py                # AWS service clients (S3, Cognito, etc.)
│   ├── models/
│   │   └── models.py             # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── services/
│   │   ├── assessment_service.py  # Business logic for assessments
│   │   ├── threat_service.py      # Threat matching & scoring
│   │   ├── evidence_service.py    # S3 upload handling
│   │   ├── audit_service.py       # Audit log recording
│   │   └── intelligence.py        # Placeholder for Phase 1 AI logic
│   ├── workers/
│   │   └── (placeholder for Phase 1 async workers)
│   ├── db/
│   │   ├── database.py           # SQLAlchemy engine & session
│   │   └── alembic/              # Migrations
│   │       ├── env.py
│   │       ├── versions/
│   │       │   └── 0001_initial.py
│       └── alembic.ini
├── tests/
│   ├── test_assessments.py       # API tests
│   ├── test_threats.py
│   ├── test_evidence.py
│   └── conftest.py               # pytest fixtures
└── requirements.txt (or pyproject.toml)
```

## Key Endpoints (Phase 0 MVP)

### Auth
- `POST /api/v1/auth/login` — Cognito/OIDC redirect or dev login
- `GET /api/v1/auth/me` — Current user profile

### Assessments
- `POST /api/v1/assessments` — Create assessment
- `GET /api/v1/assessments` — List assessments
- `GET /api/v1/assessments/{id}` — Get assessment details
- `PATCH /api/v1/assessments/{id}` — Update assessment
- `DELETE /api/v1/assessments/{id}` — Delete assessment

### Threats
- `POST /api/v1/assessments/{id}/threats` — Add threat
- `GET /api/v1/assessments/{id}/threats` — List threats
- `PATCH /api/v1/threats/{id}` — Update threat (likelihood/impact override)

### Evidence
- `POST /api/v1/assessments/{id}/evidence/initiate` — Get presigned S3 upload URL
- `POST /api/v1/evidence/{upload_id}/complete` — Finalize upload
- `GET /api/v1/evidence/{id}` — Get evidence metadata

### Recommendations
- `GET /api/v1/threats/{id}/recommendations` — List recommendations
- `POST /api/v1/recommendations` — Create recommendation

### Active Risk Register
- `GET /api/v1/risks` — List active risks
- `POST /api/v1/risks` — Create active risk

### Admin / Audit
- `GET /api/v1/admin/audit` — Query audit logs (auditor/admin only)

## Testing

Run unit tests locally:

```bash
docker-compose exec backend pytest backend/tests -v
```

Run with coverage:

```bash
docker-compose exec backend pytest backend/tests --cov=backend/app --cov-report=html
```

## AWS Setup Summary (for reference)

Your AWS account (`031195399879`) should have pre-configured:
- **RDS Aurora Serverless v2** (Postgres, ca-central-1)
- **S3 bucket** for evidence (SSE-KMS encryption)
- **Cognito user pool** for authentication
- **Secrets Manager** for DB credentials & API keys
- **KMS CMK** for encryption at rest
- **IAM roles**: ECS task role, S3 access, Cognito integration
- **CloudWatch** for logging and monitoring

## Environment Variables

See `.env.example`. Key variables:

- `DATABASE_URL` — PostgreSQL connection string
- `AWS_REGION` — ca-central-1
- `S3_BUCKET_EVIDENCE` — Evidence upload bucket
- `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID` — Authentication
- `JWT_SECRET_KEY` — Local dev only
- `DEBUG`, `LOG_LEVEL` — Debugging

## CI/CD & Deployment (Phase 0)

- GitHub Actions workflows (`.github/workflows/`) — lint, test, build
- Terraform modules in `infra/` — Infrastructure as Code
- Deploy to ECS Fargate on AWS (staging environment)

See `docs/DEPLOYMENT.md` for detailed CI/CD and staging deployment steps.

## Troubleshooting

### Database connection error

```bash
# Check Postgres is running
docker ps | grep postgres

# Restart containers
docker-compose restart postgres backend
```

### Alembic migration fails

```bash
# Reset migrations (dev only)
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

### S3 / Cognito not accessible

Ensure AWS CLI is configured:

```bash
aws configure
aws s3 ls  # Verify access
```

## Phase 1 Roadmap (Future)

- Textract integration for document OCR
- Bedrock/SageMaker for threat matching & likelihood suggestions
- LLM-based recommendation generation
- Step Functions orchestration for async workflows
- OpenSearch for full-text search and vector similarity
- Email notifications and webhooks

## Documentation

- `docs/ARCHITECTURE.md` — System design and component interactions
- `docs/DEPLOYMENT.md` — AWS deployment and CI/CD setup
- `docs/API_SPEC.md` — Full OpenAPI specification
- `docs/THREAT_CATALOGUE.md` — Threat catalogue reference

## Contributing

1. Create a feature branch: `git checkout -b feature/xyz`
2. Run tests and lint before committing
3. Submit a pull request with detailed description

## License

MIT

## Support

For issues or questions, contact the development team at dev@compliance-platform.local
