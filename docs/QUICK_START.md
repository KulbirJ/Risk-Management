# Compliance Platform MVP - Phase 0 Quick Start Guide

## Quick Start: Local Development

### Step 1: Setup Environment

```bash
cd compliance-platform-mvp

# Windows
scripts\setup-local-dev.bat

# Linux / macOS
bash scripts/setup-local-dev.sh
```

### Step 2: Verify Backend is Running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","version":"0.1.0"}
```

### Step 3: Access Swagger API Documentation

Open browser:
```
http://localhost:8000/docs
```

### Step 4: Run Tests

```bash
docker-compose exec backend pytest backend/tests -v
```

### Step 5: Check Database

```bash
docker-compose exec postgres psql -U admin -d compliance_platform -c "\dt"
```

## Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Reset database
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Next: Add Sample Data (Phase 0)

After migrations complete, seed the threat catalogue:

```bash
# Generate SQL (show statements)
docker-compose exec backend python scripts/seed_threat_catalogue.py

# Alternative: Create sample data via API (when routers implemented)
curl -X POST http://localhost:8000/api/v1/assessments \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Assessment","overall_impact":"High"}'
```

## API Routes to Implement (Phase 0)

See `../README.md` for full endpoint list. Priority order:

1. Auth endpoints (login, me)
2. Assessment CRUD
3. Threat CRUD
4. Evidence presigned upload
5. Recommendations endpoints
6. Audit log endpoint

## Key Configuration Files

- `.env` — Environment variables (copy from .env.example)
- `docker-compose.yaml` — Local dev services
- `backend/app/core/config.py` — Application settings
- `backend/app/models/models.py` — SQLAlchemy models
- `backend/app/schemas/schemas.py` — Pydantic schemas

## Troubleshooting

**Port already in use?**
```bash
# Change ports in docker-compose.yaml or kill process:
lsof -i :8000  # Find process
kill -9 <PID>  # Kill it
```

**Postgres connection refused?**
```bash
docker-compose restart postgres
docker-compose logs postgres
```

**Alembic migration errors?**
```bash
docker-compose exec backend alembic current
docker-compose exec backend alembic history
```

See README.md for full documentation.
