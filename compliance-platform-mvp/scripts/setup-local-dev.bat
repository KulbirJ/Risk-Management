@echo off
REM Windows batch script for local development setup

echo === Compliance Platform MVP - Local Dev Setup (Windows) ===
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Docker is required. Please install Docker Desktop for Windows.
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo Docker Compose is required. Please install Docker Compose.
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.11+ is required. Please install Python.
    exit /b 1
)

REM Create .env if not exists
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo WARNING: Edit .env with your AWS/Cognito credentials before running the app.
)

REM Create directories if not exist
echo Creating necessary directories...
if not exist backend\tests mkdir backend\tests
if not exist frontend\src mkdir frontend\src
if not exist infra mkdir infra
if not exist docs mkdir docs

echo.
echo === Starting Docker Compose ===
echo This will start Postgres, Redis, and the FastAPI backend...
docker-compose up -d

echo.
echo Waiting for Postgres to be ready...
timeout /t 5 /nobreak

echo.
echo === Running Database Migrations ===
docker-compose exec -T backend alembic upgrade head

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Backend API running at: http://localhost:8000
echo   2. Swagger UI: http://localhost:8000/docs
echo   3. Health check: curl http://localhost:8000/health
echo   4. View logs: docker-compose logs -f backend
echo   5. Frontend: cd frontend && npm install && npm run dev
echo.
echo To stop: docker-compose down
echo.
