# Technical & Architectural Overview

This document provides a comprehensive technical and architectural breakdown of the Threat Risk Assessment system, including how different components work together to deliver a secure, scalable compliance platform.

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Component Breakdown](#component-breakdown)
3. [Request Flow & Data Pipeline](#request-flow--data-pipeline)
4. [Database Architecture](#database-architecture)
5. [API Structure](#api-structure)
6. [Authentication & Security](#authentication--security)
7. [Deployment Architecture](#deployment-architecture)

---

## Architectural Overview

The application follows a **decoupled (or "headless") architecture** with clear separation of concerns:

- **Presentation Layer:** Next.js frontend (browser)
- **API Gateway Layer:** AWS API Gateway (routing, CORS, rate limiting)
- **Business Logic Layer:** FastAPI backend (Lambda)
- **Data Layer:** PostgreSQL database (RDS)

This separation allows each component to be developed, deployed, and scaled independently while maintaining a clean contract via REST APIs.

### High-Level Architecture Diagram

```mermaid
graph TD
    subgraph "User's Browser"
        A[<br><b>User</b><br>Accesses the web app] --> B{Next.js Frontend};
    end

    subgraph "AWS Cloud"
        subgraph "AWS Amplify"
            B -- HTTPS Request --> C[Amplify Hosting<br><i>Serves the Next.js app</i>];
        end

        subgraph "API Layer"
            C -- API Calls<br>(/api/v1/*) --> D[API Gateway<br><i>Routes requests to Lambda</i>];
        end

        subgraph "Compute Layer"
            D -- Invokes --> E[AWS Lambda<br><i>Runs FastAPI Backend</i>];
        end

        subgraph "Data Layer"
            E -- SQL Queries --> F[RDS PostgreSQL<br><i>Stores all application data</i>];
        end
    end

    subgraph "Development & Deployment"
        G[Developer] -- git push --> H{GitHub Repository};
        H -- triggers --> I[Amplify CI/CD<br><i>Builds & deploys frontend</i>];
        I --> C;
        H -- also triggers --> J[GitHub Actions<br><i>(Future) Builds & deploys backend</i>];
        J --> E;
    end

    style A fill:#fff,stroke:#333,stroke-width:2px
    style B fill:#f0f8ff,stroke:#007acc,stroke-width:2px
    style C fill:#FF9900,stroke:#333,stroke-width:2px
    style D fill:#FF9900,stroke:#333,stroke-width:2px
    style E fill:#FF9900,stroke:#333,stroke-width:2px
    style F fill:#FF9900,stroke:#333,stroke-width:2px
    style G fill:#fff,stroke:#333,stroke-width:2px
    style H fill:#6f42c1,stroke:#fff,stroke-width:2px,color:#fff
    style I fill:#FF9900,stroke:#333,stroke-width:2px
    style J fill:#2088ff,stroke:#333,stroke-width:2px
```

---

## Component Breakdown

### 1. Frontend Layer (Next.js + React)

#### Technology Stack
- **Framework:** Next.js 14 with App Router
- **Language:** TypeScript 5.x
- **UI Library:** React 18
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios
- **Date Utilities:** date-fns

#### Architecture

The frontend follows a **component-based architecture** with the following structure:

```
frontend/
├── app/                          # Next.js app router pages
│   ├── page.tsx                  # Dashboard homepage
│   ├── assessments/
│   │   ├── page.tsx              # Assessment list view
│   │   ├── [id]/page.tsx         # Assessment detail view
│   │   └── new/page.tsx          # Create assessment form
│   ├── active-risks/             # Active risks management
│   └── audit-logs/               # Audit trail viewer
├── components/                   # Reusable React components
│   ├── Layout.tsx                # App shell with navigation
│   ├── Button.tsx                # Themed button component
│   ├── Badge.tsx                 # Status/severity indicators
│   ├── ThreatModal.tsx           # Threat create/edit dialog
│   └── ActiveRiskModal.tsx       # Risk acceptance workflow
└── lib/
    ├── api-client.ts             # Centralized API client
    └── types.ts                  # TypeScript type definitions
```

#### Key Features

- **Server-Side Rendering (SSR):** Pages are rendered on the server for better SEO and initial load performance
- **Client-Side Navigation:** React handles routing after initial load for a smooth SPA experience
- **Type Safety:** Full TypeScript coverage with strict mode enabled
- **API Client Pattern:** Centralized `APIClient` class handles all HTTP requests with consistent error handling
- **Multi-Tenancy Headers:** All API requests include `X-Tenant-ID` and `X-User-ID` headers for data isolation

#### Deployment
- **Host:** AWS Amplify (Web Compute)
- **URL:** https://main.d2kda7m9vuv8zf.amplifyapp.com/
- **Build Process:** Amplify automatically builds on git push to `main` branch
- **Environment Variables:** `NEXT_PUBLIC_API_URL` configured in `amplify.yml`

---

### 2. Backend Layer (FastAPI + Python)

#### Technology Stack
- **Framework:** FastAPI 0.104+
- **Language:** Python 3.11
- **ORM:** SQLAlchemy 2.x
- **Data Validation:** Pydantic 2.x
- **Database Driver:** psycopg2-binary
- **Lambda Adapter:** Mangum (for AWS Lambda compatibility)
- **CORS:** FastAPI CORSMiddleware

#### Architecture

The backend follows a **layered architecture pattern** with clear separation of concerns:

```
backend/app/
├── main.py                       # Application factory, CORS, lifespan
├── api/                          # Route handlers (controllers)
│   ├── assessments.py            # Assessment CRUD endpoints
│   ├── threats.py                # Threat management
│   ├── active_risks.py           # Risk acceptance workflow
│   ├── evidence.py               # Evidence attachments
│   ├── recommendations.py        # Remediation recommendations
│   └── audit_logs.py             # Audit trail queries
├── services/                     # Business logic layer
│   ├── threat_service.py         # Threat operations & validation
│   ├── assessment_service.py     # Assessment lifecycle
│   └── risk_service.py           # Risk calculations
├── models/                       # SQLAlchemy ORM models
│   └── models.py                 # 8 database tables
├── schemas/                      # Pydantic models for validation
│   └── schemas.py                # Request/response DTOs
├── db/                           # Database configuration
│   └── database.py               # SQLAlchemy engine & session
├── core/                         # Configuration & utilities
│   ├── config.py                 # Settings from env vars
│   └── aws.py                    # AWS SDK clients
└── utils/
    └── helpers.py                # Shared utility functions
```

#### Layered Architecture Explained

**1. API Layer (`api/`):**
- Handles HTTP request/response
- Validates headers (tenant/user context)
- Extracts query parameters and request body
- Delegates to service layer
- Returns appropriate HTTP status codes

**2. Service Layer (`services/`):**
- Contains all business logic
- Validates domain rules
- Orchestrates database operations
- Performs calculations (CVSS scoring, risk ratings)
- Enforces authorization policies

**3. Data Layer (`models/`):**
- SQLAlchemy ORM models represent database tables
- Defines relationships between entities
- Handles database queries through the ORM

**4. Schema Layer (`schemas/`):**
- Pydantic models define API contracts
- Automatic request validation
- Response serialization
- Type safety and documentation

#### Key Features

- **Dependency Injection:** FastAPI's `Depends()` manages database sessions and context
- **Multi-Tenancy:** Tenant isolation at query level (all queries filtered by `tenant_id`)
- **Automatic Documentation:** OpenAPI/Swagger docs auto-generated from type hints
- **Type Safety:** Full Python type hints for IDE support and validation
- **Error Handling:** Consistent HTTP error responses with detail messages
- **Connection Pooling:** SQLAlchemy manages database connections efficiently

#### Deployment
- **Host:** AWS Lambda (serverless compute)
- **Entry Point:** Mangum adapter wraps FastAPI for Lambda compatibility
- **API Gateway:** HTTP API (ID: `oyxvwg62f7`) routes requests to Lambda
- **Base URL:** https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com
- **Memory:** 512 MB
- **Timeout:** 30 seconds

---

### 3. Database Layer (PostgreSQL)

#### Technology Stack
- **Service:** AWS RDS (Relational Database Service)
- **Engine:** PostgreSQL 14.x
- **Connection:** SQLAlchemy ORM via psycopg2 driver
- **Region:** ca-west-1 (Canada West)

#### Database Schema

The database consists of **8 core tables** with relationships enforcing referential integrity:

```
┌──────────────┐
│   Tenants    │ (Multi-tenant organizations)
└───────┬──────┘
        │ 1:N
        ├──────────────┬──────────────┬──────────────┐
        │              │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│    Users     │ │Assessments│ │ActiveRisks│ │ AuditLogs │
└───────┬──────┘ └─────┬─────┘ └───────────┘ └───────────┘
        │ 1:N          │ 1:N
        │              │
    ┌───▼───────────┬──▼────────────┬──────────────┐
    │               │               │              │
┌───▼────┐   ┌─────▼────┐   ┌──────▼────┐   ┌───▼─────────┐
│Threats │   │ Evidence │   │Recommenda-│   │ThreatCatalogue│
│        │───┤          │   │  tions    │   │   (Lookup)   │
└────────┘   └──────────┘   └───────────┘   └──────────────┘
```

#### Table Details

**1. Tenants**
- Purpose: Multi-tenant organization isolation
- Key Columns: `id`, `name`, `region`, `settings` (JSONB)
- Relationships: Parent to all tenant-scoped entities

**2. Users**
- Purpose: User accounts within tenants
- Key Columns: `id`, `tenant_id`, `email`, `display_name`, `roles` (JSONB), `cognito_sub`
- Unique Constraint: `(email, tenant_id)` - users unique per tenant
- Relationships: Owns assessments, creates threats/evidence

**3. Assessments**
- Purpose: Security assessment projects
- Key Columns: `id`, `tenant_id`, `owner_user_id`, `title`, `status`, `overall_impact`, `tech_stack` (JSONB)
- Status Values: `draft`, `in_progress`, `in_review`, `completed`, `archived`
- Relationships: Contains threats, evidence, recommendations

**4. Threats**
- Purpose: Identified security threats within assessments
- Key Columns: `id`, `assessment_id`, `title`, `description`, `recommendation`, `likelihood`, `impact`, `severity`, `cvss_score`, `cve_ids` (JSONB)
- Calculated Fields: `severity` auto-computed from likelihood + impact
- Relationships: Belongs to assessment, links to evidence

**5. Evidence**
- Purpose: Supporting documentation for threats/assessments
- Key Columns: `id`, `assessment_id`, `threat_id`, `file_path`, `s3_key`, `uploaded_by_user_id`
- Storage: Files stored in S3, metadata in database

**6. Recommendations**
- Purpose: Remediation action items
- Key Columns: `id`, `assessment_id`, `threat_id`, `title`, `priority`, `status`, `assigned_to_user_id`
- Status Values: `open`, `in_progress`, `completed`, `deferred`, `wont_fix`

**7. ActiveRisks**
- Purpose: Accepted risks with business justification
- Key Columns: `id`, `tenant_id`, `assessment_id`, `threat_id`, `acceptance_rationale`, `accepted_by_user_id`, `expiry_date`
- Purpose: Track risks accepted by business owners

**8. AuditLogs**
- Purpose: Immutable audit trail for compliance
- Key Columns: `id`, `tenant_id`, `actor_user_id`, `action`, `entity_type`, `entity_id`, `changes` (JSONB), `ip_address`
- Retention: Configurable per tenant settings

**9. ThreatCatalogue**
- Purpose: Knowledge base of common threats (OWASP, MITRE ATT&CK)
- Key Columns: `catalogue_key`, `title`, `description`, `category`, `default_likelihood`
- Used for: Auto-suggestions when creating threats

#### Data Isolation

**Multi-Tenancy Strategy:**
- Every tenant-scoped table includes `tenant_id` foreign key
- All queries automatically filtered by tenant context from headers
- Database-level foreign key constraints prevent cross-tenant references
- SQLAlchemy query filters enforce tenant isolation

**Query Example:**
```python
# All queries include tenant filter
db.query(Assessment).filter(
    Assessment.tenant_id == tenant_id,
    Assessment.id == assessment_id
).first()
```

---

### 4. API Gateway Layer

#### Configuration
- **Type:** HTTP API (simpler, lower latency than REST API)
- **API ID:** oyxvwg62f7
- **Region:** ca-west-1
- **Auto-Deploy:** Enabled (changes deploy immediately)

#### CORS Configuration
```json
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  "AllowHeaders": ["content-type", "x-tenant-id", "x-user-id", "authorization"],
  "AllowCredentials": false,
  "MaxAge": 300
}
```

#### Route Configuration
- **Default Route:** `$default` → Lambda integration
- **All Paths:** `/*` → Routes to compliance-platform-api Lambda
- **Headers Passed:** All headers forwarded to Lambda including custom headers

---

## Request Flow & Data Pipeline

### End-to-End Request Example: Fetching Assessment Details

Let's trace a complete request from user click to database and back:

**Step 1: User Action**
```
User clicks on an assessment in the dashboard
→ React Router navigates to /assessments/[id]
```

**Step 2: Frontend Request**
```typescript
// frontend/lib/api-client.ts
async getAssessment(id: string): Promise<Assessment> {
  const { data } = await this.client.get(`/assessments/${id}`);
  // Axios automatically includes:
  // - X-Tenant-ID: 67636bd3-9846-4bde-806f-aea369fc9457
  // - X-User-ID: 0bc9d6a9-f342-452e-9297-ee33f44d4f84
  return data;
}
```

**Step 3: HTTP Request**
```
GET https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com/api/v1/assessments/{id}
Headers:
  X-Tenant-ID: 67636bd3-9846-4bde-806f-aea369fc9457
  X-User-ID: 0bc9d6a9-f342-452e-9297-ee33f44d4f84
  Content-Type: application/json
```

**Step 4: API Gateway Processing**
```
1. CORS preflight check (if needed)
2. Route matching: /api/v1/assessments/{id}
3. Lambda invocation with event payload
```

**Step 5: Lambda Invocation**
```python
# Mangum adapter converts API Gateway event to ASGI request
# FastAPI receives standard HTTP request

# backend/app/api/assessments.py
@router.get("/{assessment_id}", response_model=AssessmentRead)
def get_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    context: tuple[UUID, UUID] = Depends(get_tenant_context)
):
    tenant_id, user_id = context  # Extracted from headers
    
    # Service layer handles business logic
    assessment = AssessmentService.get_assessment(
        db=db,
        assessment_id=assessment_id,
        tenant_id=tenant_id
    )
    
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    return assessment  # Pydantic serializes to JSON
```

**Step 6: Service Layer**
```python
# backend/app/services/assessment_service.py
@staticmethod
def get_assessment(db: Session, assessment_id: UUID, tenant_id: UUID):
    return db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.tenant_id == tenant_id  # Tenant isolation
    ).first()
```

**Step 7: Database Query**
```sql
SELECT 
  id, tenant_id, owner_user_id, title, description,
  system_background, scope, tech_stack, overall_impact,
  status, created_at, updated_at
FROM assessments
WHERE id = '65c6a4bc-042f-44fb-ab6a-c0e91376f502'
  AND tenant_id = '67636bd3-9846-4bde-806f-aea369fc9457';
```

**Step 8: Response Pipeline**
```
Database Row → SQLAlchemy ORM Model → Pydantic Schema → JSON
→ Lambda Response → API Gateway → Frontend Axios → React State
```

**Step 9: Frontend Rendering**
```typescript
// frontend/app/assessments/[id]/page.tsx
const [assessment, setAssessment] = useState<Assessment | null>(null);

useEffect(() => {
  const loadData = async () => {
    const data = await apiClient.getAssessment(assessmentId);
    setAssessment(data);  // Triggers re-render
  };
  loadData();
}, [assessmentId]);

// React renders the assessment details
```

### Performance Characteristics

- **Cold Start:** 2-3 seconds (Lambda init + database connection)
- **Warm Response:** 10-50ms (Lambda execution only)
- **Database Query:** 5-15ms typical
- **Total Round Trip:** 50-200ms (warm Lambda)

---

## API Structure

### Base URL
```
https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com/api/v1
```

### Core Endpoints

#### Assessments
- `GET /assessments` - List all assessments for tenant
- `GET /assessments/{id}` - Get assessment details
- `POST /assessments` - Create new assessment
- `PATCH /assessments/{id}` - Update assessment
- `DELETE /assessments/{id}` - Delete assessment (soft delete)

#### Threats
- `GET /threats?assessment_id={id}` - List threats for an assessment
- `GET /threats/{id}` - Get threat details
- `POST /threats?assessment_id={id}` - Create new threat
- `PATCH /threats/{id}` - Update threat
- `DELETE /threats/{id}` - Delete threat

#### Active Risks
- `GET /active-risks?status={status}` - List accepted risks
- `GET /active-risks/{id}` - Get risk details
- `POST /active-risks?assessment_id={id}` - Create risk acceptance
- `POST /active-risks/{id}/accept` - Accept a risk with justification
- `PATCH /active-risks/{id}` - Update risk acceptance
- `DELETE /active-risks/{id}` - Remove risk acceptance

#### Evidence
- `GET /evidence?assessment_id={id}` - List evidence
- `POST /evidence` - Upload evidence (S3 + metadata)
- `DELETE /evidence/{id}` - Delete evidence

#### Recommendations
- `GET /recommendations?assessment_id={id}` - List recommendations
- `POST /recommendations` - Create recommendation
- `PATCH /recommendations/{id}` - Update recommendation
- `DELETE /recommendations/{id}` - Delete recommendation

#### Audit Logs
- `GET /audit-logs` - List audit events (filterable)

### Administrative Endpoints

#### Health Check
- `GET /health` - Service health status

#### Database Seeding
- `POST /seed` - Create test tenant and user (idempotent)

#### Schema Migration
- `POST /migrate-schema` - Add missing database columns (idempotent)

### Request/Response Format

**Standard Request Headers:**
```
Content-Type: application/json
X-Tenant-ID: {tenant-uuid}
X-User-ID: {user-uuid}
```

**Standard Success Response:**
```json
{
  "id": "uuid",
  "title": "string",
  "status": "enum",
  "created_at": "2026-02-10T18:00:00Z",
  "updated_at": "2026-02-10T18:30:00Z"
}
```

**Standard Error Response:**
```json
{
  "detail": "Error message explaining what went wrong"
}
```

---

## Authentication & Security

### Current Implementation: Mock Authentication

**Status:** Mock authentication enabled for MVP testing

**Configuration:**
- Frontend: `NEXT_PUBLIC_USE_MOCK_AUTH=true`
- Hardcoded Credentials in API Client:
  - Tenant ID: `67636bd3-9846-4bde-806f-aea369fc9457`
  - User ID: `0bc9d6a9-f342-452e-9297-ee33f44d4f84`

**How It Works:**
1. Frontend includes tenant/user IDs in all API requests as headers
2. Backend extracts context from `X-Tenant-ID` and `X-User-ID` headers
3. All queries filtered by tenant ID for data isolation
4. No actual authentication validation (trust-based)

### Future: AWS Cognito Integration

**Planned Architecture:**
1. **User Signup/Login:** Cognito User Pools
2. **JWT Tokens:** Frontend receives JWT from Cognito
3. **Authorization Header:** `Authorization: Bearer {jwt-token}`
4. **Backend Validation:**
   - Verify JWT signature with Cognito public keys
   - Extract `cognito_sub` (user ID) from token claims
   - Lookup user in database by `cognito_sub`
   - Extract `tenant_id` from user record
5. **Multi-Factor Authentication:** Cognito MFA support

### Security Measures

**Current:**
- ✅ HTTPS only (enforced by AWS)
- ✅ CORS configured (prevents unauthorized domain access)
- ✅ Tenant isolation at database query level
- ✅ SQL injection prevention (SQLAlchemy parameterized queries)
- ✅ Input validation (Pydantic schemas)
- ✅ No sensitive data in logs

**Pending:**
- ⏳ Real authentication (Cognito integration)
- ⏳ Role-based access control (RBAC)
- ⏳ API rate limiting
- ⏳ Secrets management (AWS Secrets Manager for DB credentials)
- ⏳ Audit logging for all mutations

---

## Deployment Architecture

### Deployment Environments

**Production (Current):**
- **Frontend:** AWS Amplify → `main.d2kda7m9vuv8zf.amplifyapp.com`
- **Backend:** AWS Lambda in `ca-west-1`
- **Database:** RDS PostgreSQL in `ca-west-1`
- **Branch:** `main` branch of GitHub repository

**Local Development:**
- **Frontend:** `npm run dev` at localhost:3000
- **Backend:** Docker Compose with Postgres
- **Database:** Local PostgreSQL container

### CI/CD Pipeline

#### Frontend Deployment (Automated)
```
1. Developer pushes to GitHub main branch
2. Amplify webhook triggers build
3. Amplify runs build:
   - npm install
   - npm run build
   - Environment variables injected
4. Deploy to Amplify hosting
5. DNS updated automatically
```

**Build Configuration:** See `amplify.yml`

#### Backend Deployment (Manual - Current)
```
1. Developer pushes to GitHub main branch
2. GitHub webhook triggers (manual watch)
3. AWS re-deploys Lambda function from latest code
4. API Gateway routes updated (auto-deploy enabled)
```

**Future:** GitHub Actions workflow for automated backend deployment

### Infrastructure Components

| Component | Service | Region | Purpose |
|-----------|---------|--------|---------|
| Frontend Hosting | AWS Amplify | Global CDN | Next.js app delivery |
| API Gateway | HTTP API | ca-west-1 | Request routing, CORS |
| Compute | Lambda | ca-west-1 | FastAPI backend execution |
| Database | RDS PostgreSQL | ca-west-1 | Data persistence |
| File Storage | S3 (planned) | ca-west-1 | Evidence attachments |
| Logs | CloudWatch | ca-west-1 | Application logs |

### Scalability Characteristics

- **Frontend:** Global CDN, scales automatically
- **API Gateway:** Scales to millions of requests
- **Lambda:** Auto-scales 0-1000+ concurrent executions
- **RDS:** Single instance (upgradeable to Multi-AZ, read replicas)

### Cost Optimization

- **Serverless Backend:** Pay only for Lambda execution time (no idle costs)
- **RDS:** db.t3.micro (free tier eligible for 12 months)
- **Amplify:** 1000 build minutes/month free, then $0.01/minute
- **API Gateway:** $1 per million requests

---

## Technology Integration Summary

### How Components Work Together

1. **User Interaction → Frontend**
   - React components render UI
   - User actions trigger event handlers
   - Event handlers call API client methods

2. **Frontend → API Gateway**
   - Axios sends HTTP requests with headers
   - API Gateway validates CORS
   - Routes request to Lambda

3. **API Gateway → Lambda**
   - Converts HTTP to Lambda event
   - Mangum adapts event to ASGI
   - FastAPI receives request

4. **Lambda → Database**
   - SQLAlchemy creates connection from pool
   - ORM translates Python to SQL
   - PostgreSQL executes query

5. **Database → Lambda**
   - Query results returned as rows
   - SQLAlchemy maps to Python objects
   - Pydantic serializes to JSON

6. **Lambda → Frontend**
   - FastAPI returns HTTP response
   - API Gateway forwards response
   - Axios resolves promise
   - React updates state and re-renders

### Key Integration Points

- **Mangum:** Bridges FastAPI (ASGI) ↔ Lambda (event-driven)
- **SQLAlchemy:** Bridges Python ↔ PostgreSQL
- **Pydantic:** Bridges Python ↔ JSON (validation + serialization)
- **Axios:** Bridges React ↔ HTTP API
- **API Gateway:** Bridges Internet ↔ Lambda

### Data Flow Diagram

```
┌──────────┐    HTTPS     ┌─────────────┐    Lambda      ┌──────────┐
│          │────────────> │   API       │──────Event────> │  Lambda  │
│ Browser  │              │  Gateway    │                 │ (FastAPI)│
│          │ <────────────│             │ <─────JSON───── │          │
└──────────┘    JSON      └─────────────┘                 └────┬─────┘
     ▲                                                          │ SQL
     │                                                          ▼
     │                                                   ┌─────────────┐
     │                                                   │  PostgreSQL │
     │                                                   │     RDS     │
     └───────────── User sees updated UI ───────────────└─────────────┘
```

---

## Conclusion

This architecture provides a solid foundation for a scalable, secure compliance platform. The decoupled design allows independent scaling of frontend and backend, while the serverless backend minimizes operational overhead and costs. As the application grows, components can be enhanced (e.g., adding Cognito auth, implementing caching, adding read replicas) without major architectural changes.
