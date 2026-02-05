#!/bin/bash
# Local development setup script for Compliance Platform MVP

set -e

echo "=== Compliance Platform MVP - Local Dev Setup ==="

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Docker is required. Please install Docker."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required. Please install Docker Compose."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required. Please install Python 3.11+."; exit 1; }

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Edit .env with your AWS/Cognito credentials before running the app."
fi

# Create directories if not exist
echo "Creating necessary directories..."
mkdir -p backend/tests
mkdir -p frontend/src
mkdir -p infra
mkdir -p docs

echo ""
echo "=== Starting Docker Compose ==="
echo "This will start Postgres, Redis, and the FastAPI backend..."
docker-compose up -d

echo ""
echo "Waiting for Postgres to be ready..."
sleep 5

# Run migrations
echo ""
echo "=== Running Database Migrations ==="
docker-compose exec -T backend alembic upgrade head || echo "⚠️  Migrations may have issues. Check logs."

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "  1. Backend API running at: http://localhost:8000"
echo "  2. Swagger UI: http://localhost:8000/docs"
echo "  3. Health check: curl http://localhost:8000/health"
echo "  4. View logs: docker-compose logs -f backend"
echo "  5. Frontend: cd frontend && npm install && npm run dev"
echo ""
echo "🛑 To stop: docker-compose down"
