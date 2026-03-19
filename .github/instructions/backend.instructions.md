---
applyTo: "backend/**"
---

# Backend Development Instructions

These instructions apply whenever you are editing files under `backend/`.

---

## Layered Architecture — always follow this

```
backend/app/api/        ← thin route handlers only (no business logic)
backend/app/services/   ← all business logic, scoring, validation
backend/app/models/     ← SQLAlchemy ORM models
backend/app/schemas/    ← Pydantic v2 request/response schemas
backend/app/core/       ← config.py (settings), aws.py (boto3 clients)
backend/app/utils/      ← shared helpers
```

**Rule:** Route handlers call service functions. Service functions call ORM. Never put business logic directly in route handlers.

---

## Route Handler Pattern

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import MySchema, MyCreateSchema
from app.services import my_service

router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

@router.get("/", response_model=list[MySchema])
def list_resources(
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    return my_service.list_resources(db, tenant_id=tenant_id)
```

- Always declare `tenant_id` and `user_id` from request headers.
- Always pass `tenant_id` to every service call.
- Use `response_model=` on every endpoint.
- Use `HTTPException(status_code=404)` for not-found, `422` for validation, `403` for authorization.

---

## Multi-Tenancy — non-negotiable

Every query **must** filter by `tenant_id`. Never return data across tenant boundaries.

```python
# CORRECT
stmt = select(Assessment).where(
    Assessment.tenant_id == tenant_id,
    Assessment.id == assessment_id,
)
result = db.execute(stmt).scalar_one_or_none()
if result is None:
    raise HTTPException(status_code=404, detail="Not found")

# WRONG — never do this
result = db.get(Assessment, assessment_id)
```

---

## SQLAlchemy 2.x Style

Use the modern execution API — never legacy `session.query()`.

```python
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

# SELECT
stmt = select(Threat).where(Threat.assessment_id == assessment_id, Threat.tenant_id == tenant_id)
threats = db.execute(stmt).scalars().all()

# INSERT
db.add(new_threat)
db.commit()
db.refresh(new_threat)

# UPDATE
stmt = (
    update(Threat)
    .where(Threat.id == threat_id, Threat.tenant_id == tenant_id)
    .values(status="resolved")
    .returning(Threat)
)
threat = db.execute(stmt).scalar_one()
db.commit()
```

---

## Audit Logging — required on every write

Write an `AuditLog` entry for every create, update, and delete. Do this inside the service layer, in the same transaction.

```python
from app.models.models import AuditLog
import json

audit = AuditLog(
    action="CREATE",           # "CREATE" | "UPDATE" | "DELETE"
    entity_type="Threat",
    entity_id=str(new_threat.id),
    old_value=None,            # None for CREATE
    new_value=json.dumps(threat_dict),
    actor_id=user_id,
    tenant_id=tenant_id,
)
db.add(audit)
db.commit()
```

---

## Pydantic v2 Schemas

All schemas live in `backend/app/schemas/schemas.py`. Use and extend existing schemas before creating new ones.

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ThreatCreate(BaseModel):
    title: str
    description: str | None = None
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)

class ThreatResponse(ThreatCreate):
    id: UUID
    assessment_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

Always set `model_config = {"from_attributes": True}` on response schemas so SQLAlchemy ORM objects serialize correctly.

---

## Database Model Conventions

All models are in `backend/app/models/models.py`.

- UUID primary keys using `default=uuid.uuid4`
- `tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, index=True)`
- `created_at = Column(DateTime, default=datetime.utcnow)`
- `updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)`

**Key relationship chain:** `Tenant → Assessment → Threat → Evidence / Recommendation / ActiveRisk`

---

## Environment Config

Settings are loaded from environment variables via Pydantic Settings in `backend/app/core/config.py`. In production, secrets come from AWS Secrets Manager. Never hardcode credentials.

```python
from app.core.config import settings
db_url = settings.DATABASE_URL
```

---

## Testing Conventions

- Tests live in `backend/tests/`.
- Use `pytest` + `TestClient` for API integration tests.
- Use `moto` to mock all AWS services (S3, Cognito, Secrets Manager).
- Always set `X-Tenant-ID` and `X-User-ID` headers in test requests.
- Test multi-tenant isolation: verify tenant A cannot access tenant B's data.

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_assessments():
    response = client.get(
        "/api/v1/assessments/",
        headers={"X-Tenant-ID": "test-tenant-id", "X-User-ID": "test-user-id"},
    )
    assert response.status_code == 200
```

---

## Code Quality

| Tool | Purpose | Config |
|---|---|---|
| **Ruff** | Linting | `pyproject.toml` |
| **Black** | Formatting | `pyproject.toml` |
| **mypy** | Type checking | `pyproject.toml` |
| **Bandit** | Security scanning | CI only |

Run locally: `ruff check backend/` · `black backend/` · `mypy backend/`

---

## Phase 1 Code (do not modify unless working on Phase 1)

These files exist but are **not yet wired up** to the main app:
- `backend/app/api/attack.py` — MITRE ATT&CK mappings
- `backend/app/api/intelligence.py` — threat intelligence enrichment
- `backend/app/api/graph.py` — kill chain visualization
- `backend/app/api/clusters.py` — threat clustering
- `backend/app/api/ml.py` — ML scoring
- `backend/app/api/intel.py` — intel enrichment

These are Phase 1 features using AWS Bedrock + Textract. Don't modify them for Phase 0 work.
