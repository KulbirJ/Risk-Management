# Compliance Platform - Complete Setup Guide

This is a complete threat risk assessment and compliance management platform with a FastAPI backend and Next.js frontend.

## 🏗️ Architecture

- **Backend**: FastAPI + PostgreSQL + Redis (Docker Compose)
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Authentication**: AWS Cognito JWT (with local development fallback)
- **Storage**: AWS S3 for evidence files
- **Database**: PostgreSQL with SQLAlchemy ORM

## 📋 Prerequisites

- Docker Desktop (for backend)
- Node.js 18+ (for frontend)
- Python 3.11+ (for backend development)
- AWS Account (optional, for Cognito and S3)

## 🚀 Quick Start

### 1. Start Backend Services

```bash
cd compliance-platform-mvp
docker-compose up -d
```

This starts:
- Backend API on http://localhost:8000
- PostgreSQL on localhost:5432
- Redis on localhost:6379

Verify backend is running:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:3000

### 3. Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

For local development (no Cognito), the app uses mock authentication with the test tenant and user already created in your database.

## 🔑 Authentication Modes

### Local Development (Mock Auth)
- **Status**: ✅ Active by default
- **Configuration**: Already set in `frontend/.env.local`
- **Test Credentials**: Pre-configured tenant/user IDs
- **Usage**: Perfect for development and testing

### Production (AWS Cognito)
1. Create AWS Cognito User Pool in ca-west-1
2. Update `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_COGNITO_USER_POOL_ID=your-pool-id
   NEXT_PUBLIC_COGNITO_CLIENT_ID=your-client-id
   NEXT_PUBLIC_USE_MOCK_AUTH=false
   ```
3. Update `backend/.env`:
   ```env
   COGNITO_USER_POOL_ID=your-pool-id
   COGNITO_CLIENT_ID=your-client-id
   COGNITO_REGION=ca-west-1
   ```
4. Restart both backend and frontend

## 📊 Test Data

Your database already has test data:

**Tenant:**
- ID: `67636bd3-9846-4bde-806f-aea369fc9457`
- Name: Test Organization

**User:**
- ID: `0bc9d6a9-f342-452e-9297-ee33f44d4f84`
- Email: test@example.com
- Roles: assessor, reviewer

**Sample Assessment:**
- ID: `e55726e3-68cd-4519-9943-2b5e6867cfa3`
- Name: Web Application Security Assessment

## 🎯 Key Features

### ✅ Implemented Features

1. **Assessments Management**
   - Create, view, edit, delete assessments
   - Track status (draft, in_progress, completed, archived)
   - Set risk appetite and target dates

2. **Threat Tracking**
   - Identify threats with categories
   - Automatic severity calculation (likelihood × impact)
   - Link to affected assets and existing controls

3. **Evidence Management**
   - Upload files to S3 with presigned URLs
   - Link evidence to assessments and threats
   - Support multiple file types (documents, screenshots, logs, scans)

4. **Recommendations**
   - Create remediation recommendations
   - Track priority and status
   - Link to specific threats
   - Set responsible parties and target dates

5. **Risk Register**
   - Active risk tracking
   - Risk acceptance workflow
   - Residual risk assessment
   - Risk owner assignment

6. **Audit Logs**
   - Immutable change tracking
   - Complete entity history
   - Filter by action, entity type, actor
   - Old/new value comparison

7. **Authentication & Authorization**
   - AWS Cognito JWT validation
   - User auto-provisioning on first login
   - Role-based access control (RBAC)
   - Multi-tenant isolation

## 🛠️ Development

### Backend Development

```bash
# Install dependencies
pip install -e .

# Run migrations
cd backend/app/db/alembic
alembic upgrade head

# Run tests (coming soon)
pytest
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Database Migrations

```bash
cd backend/app/db/alembic

# Create new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 📁 Project Structure

```
compliance-platform-mvp/
├── backend/
│   ├── app/
│   │   ├── api/              # REST API endpoints
│   │   ├── core/             # Core functionality (auth, config)
│   │   ├── db/               # Database models and migrations
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic layer
│   │   └── utils/            # Utilities (S3, etc.)
│   └── tests/                # Test suite
├── frontend/
│   ├── app/                  # Next.js 14 App Router
│   ├── components/           # React components
│   └── lib/                  # API client, types, utils
├── docker/                   # Docker configuration
├── infra/                    # Infrastructure as Code
└── docker-compose.yml        # Container orchestration
```

## 🌐 API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📱 Frontend Pages

- `/` - Dashboard with metrics
- `/assessments` - Assessment list
- `/assessments/new` - Create assessment
- `/assessments/[id]` - Assessment detail with threats
- `/active-risks` - Risk register
- `/audit-logs` - Audit log viewer

## 🔒 Environment Variables

### Backend (`.env`)
```env
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/compliance_db

# Redis
REDIS_URL=redis://redis:6379/0

# AWS
AWS_REGION=ca-west-1
COGNITO_USER_POOL_ID=your-pool-id
COGNITO_CLIENT_ID=your-client-id
S3_BUCKET_EVIDENCE=compliance-platform-dev-evidence

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Frontend (`.env.local`)
```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# AWS Cognito
NEXT_PUBLIC_AWS_REGION=ca-west-1
NEXT_PUBLIC_COGNITO_USER_POOL_ID=
NEXT_PUBLIC_COGNITO_CLIENT_ID=

# Mock Auth (for local dev)
NEXT_PUBLIC_USE_MOCK_AUTH=true
NEXT_PUBLIC_MOCK_TENANT_ID=67636bd3-9846-4bde-806f-aea369fc9457
NEXT_PUBLIC_MOCK_USER_ID=0bc9d6a9-f342-452e-9297-ee33f44d4f84
```

## 🐛 Troubleshooting

### Backend Issues

**Docker containers not starting:**
```bash
docker-compose down
docker-compose up -d --build
```

**Database connection errors:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs postgres
```

**CORS errors:**
- Verify `CORS_ORIGINS` in backend `.env` includes frontend URL

### Frontend Issues

**Build errors:**
```bash
# Clear cache and rebuild
rm -rf .next node_modules
npm install
npm run dev
```

**API connection errors:**
- Verify backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify CORS settings on backend

**Authentication errors:**
- For mock auth: Verify tenant and user IDs exist in database
- For Cognito: Verify User Pool and Client IDs are correct

## 📈 Next Steps

1. **Configure AWS Cognito** for production authentication
2. **Set up S3 bucket** for evidence file storage
3. **Deploy to AWS** using ECS Fargate
4. **Set up CI/CD** pipeline with GitHub Actions
5. **Add automated tests** for backend and frontend
6. **Configure monitoring** with CloudWatch or similar

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests (when available)
4. Submit a pull request

## 📄 License

MIT

## 🆘 Support

For issues or questions:
1. Check this README
2. Review API docs at http://localhost:8000/docs
3. Check Docker logs: `docker-compose logs`
4. Review frontend console in browser DevTools

---

**Current Status:** ✅ MVP Complete
- Backend: All Phase 1 APIs implemented
- Frontend: Full UI with all features
- Authentication: Cognito JWT + mock auth for local dev
- Database: 9 tables with sample data
- Docker: All services containerized

Ready for development and testing! 🚀
