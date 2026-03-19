# Copilot Instructions — Threat Risk Assessment / Compliance Platform

## Project Purpose
A **cybersecurity risk assessment and compliance management platform** that helps organizations identify, assess, and manage technology risks.
Users describe their tech environment; the system identifies threats using a threat catalogue, scores severity via rule-based algorithms, and recommends mitigations.
Tracked risks that cannot be immediately resolved live in an **Active Risk Register** until resolved.

**Current Phase:** Phase 0 MVP — manual threat entry, rule-based scoring, full CRUD.
**Future Phases:** Phase 1+ adds AI/ML enrichment via AWS Bedrock, Textract, and LLM analysis. Several Phase 1 components already exist in the codebase but are not yet wired up.

---

## Tech Stack (quick reference)

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 · React 18 · TypeScript 5 · Tailwind CSS · Axios |
| Backend | FastAPI 0.104+ · Python 3.11 · SQLAlchemy 2.x · Pydantic 2.x · Alembic |
| Database | PostgreSQL 15 (local Docker) · Aurora Serverless v2 (AWS prod) |
| Caching | Redis 7 |
| Auth | AWS Cognito (JWT) — header fallback in dev |
| Cloud | AWS: S3 · Cognito · Secrets Manager · KMS · CloudWatch · Lambda · API Gateway · Amplify |
| DevOps | Docker · Docker Compose · Terraform (infra/) · GitHub Actions (3 workflows) |
| Lambda adapter | Mangum (wraps FastAPI for Lambda) |

**AWS Region:** `ca-central-1` · **Account:** `031195399879`

---

## Architecture

```
Browser
  └─► AWS Amplify (Next.js frontend)
        └─► API Gateway
              └─► Lambda (Mangum adapter)
                    └─► FastAPI application
                          ├─► RDS PostgreSQL (Aurora Serverless v2)
                          ├─► S3 (evidence file storage, pre-signed URLs)
                          └─► Secrets Manager / Cognito
```

**Backend internal layers:**
```
API Routes (backend/app/api/)
  └─► Service Layer (backend/app/services/)
        └─► SQLAlchemy ORM (backend/app/models/models.py)
              └─► PostgreSQL
```

---

## Cross-Cutting Patterns (apply everywhere)

### Multi-tenancy
- Every database table has a `tenant_id` foreign key — always filter queries by it.
- Every API request carries `X-Tenant-ID` and `X-User-ID` headers for context.
- Never return or modify data across tenant boundaries.

### Authentication
- **Production:** AWS Cognito JWT validation.
- **Development:** Header-based fallback with mock tenant/user IDs (no real JWT needed locally).
- RBAC roles stored as JSONB on the User model: `["admin", "assessor", "reviewer", "risk_owner", "auditor", "viewer"]`.

### API conventions
- All endpoints under `/api/v1/*`.
- RESTful conventions: GET (list/detail), POST (create), PUT (update), DELETE.
- Request and response bodies are always validated via **Pydantic v2 schemas** (`backend/app/schemas/schemas.py`).
- Consistent error responses — use FastAPI `HTTPException` with appropriate status codes.

### Database conventions
- UUID primary keys on all tables.
- `created_at` and `updated_at` timestamps on all tables.
- SQLAlchemy 2.x style: `session.execute(select(Model).where(...))` — **not** legacy `session.query()`.

### Audit logging
- Write an `AuditLog` record for every create, update, and delete operation.
- Fields: `action`, `entity_type`, `entity_id`, `old_value`, `new_value`, `actor_id`, `timestamp`.

---

## Database Models (9 tables)

| Model | Purpose |
|---|---|
| `Tenant` | Organization/account in the multi-tenant system |
| `User` | User account linked to a Tenant and Cognito sub |
| `Assessment` | A security assessment session (has many Threats) |
| `Threat` | An identified threat within an Assessment |
| `Evidence` | Uploaded files (S3) linked to an Assessment or Threat |
| `Recommendation` | Remediation advice linked to a Threat |
| `ActiveRisk` | Accepted/deferred risk in the Active Risk Register |
| `AuditLog` | Immutable change history for all entities |
| `ThreatAttackMapping` / `KillChain` | MITRE ATT&CK mappings (Phase 1) |

**Key relationship chain:** `Tenant → Assessment → Threat → Evidence / Recommendation / ActiveRisk`

---

## Repository Structure (one-liner per folder)

| Path | Contents |
|---|---|
| `backend/` | FastAPI app: `app/api/` (routes), `app/services/` (business logic), `app/models/`, `app/schemas/`, `app/core/` (config, AWS clients), `app/utils/` |
| `frontend/` | Next.js 14 App Router: `app/` (pages), `components/` (shared UI), `lib/` (API client, types) |
| `infra/` | Terraform: AWS resources (RDS, ALB, ECS Fargate, VPC) |
| `docker/` | Dockerfile for FastAPI backend |
| `scripts/` | Setup, migration, and seeding scripts (bash + PowerShell + Python) |
| `docs/` | AWS setup guides, CI/CD, testing, deployment guides |
| `e2e-tests/` | Playwright end-to-end tests |
| `lambda-current/` | Lambda deployment package (backend + all Python dependencies) |
| `.github/workflows/` | CI (`ci.yml`), staging deploy (`deploy.yml`), production release (`release.yml`) |

---

## CI/CD Overview

| Workflow | Trigger | Key jobs |
|---|---|---|
| `ci.yml` | Any push / PR | lint (Ruff, Black, mypy), test (pytest + coverage), security scan (Bandit), Docker build |
| `deploy.yml` | Push to `main` | Build → ECR push → ECS Fargate staging deploy |
| `release.yml` | Push tag `v*.*.*` | GitHub Release → ECR push → ECS Fargate production deploy (manual approval) |

---

## Common Commands

```bash
# Local dev
docker-compose up                                          # start all services (DB, Redis, API, frontend)

# Backend tests
docker-compose exec backend pytest --cov=app --cov-report=html

# Database migrations
python backend/run_migrations.py

# Seed threat catalogue
python scripts/seed_threat_catalogue.py
```
