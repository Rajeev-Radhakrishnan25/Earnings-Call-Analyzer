#!/usr/bin/env bash
# Earnings Call Analyzer - Setup and Run Script
# Usage:
#   ./start.sh setup    - First-time setup (install deps, create tables, seed data)
#   ./start.sh run      - Start backend and frontend
#   ./start.sh db       - Start only the database
#   ./start.sh seed     - Generate and load sample data
#   ./start.sh stop     - Stop all services

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[ECA]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

check_prereqs() {
    command -v docker >/dev/null 2>&1 || err "Docker is not installed. Install Docker Desktop first."
    command -v python3 >/dev/null 2>&1 || err "Python 3 is not installed."
    command -v node >/dev/null 2>&1 || err "Node.js is not installed."

    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log "Creating .env from .env.example..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        info "Edit .env and set your ANTHROPIC_API_KEY before running queries."
    fi
}

start_db() {
    log "Starting PostgreSQL + pgvector..."
    cd "$PROJECT_DIR"
    docker compose up -d
    log "Waiting for database to be ready..."
    sleep 3

    for i in $(seq 1 10); do
        if docker compose exec -T db pg_isready -U eca_user -d earnings_call_analyzer >/dev/null 2>&1; then
            log "Database is ready."
            return 0
        fi
        sleep 2
    done
    err "Database failed to start within 20 seconds."
}

setup() {
    check_prereqs
    start_db

    log "Installing backend dependencies..."
    cd "$BACKEND_DIR"
    if command -v poetry >/dev/null 2>&1; then
        poetry install
    else
        info "Poetry not found. Installing with pip instead..."
        pip3 install -e ".[dev]" 2>/dev/null || pip install fastapi uvicorn sqlalchemy asyncpg pgvector pydantic pydantic-settings anthropic sentence-transformers httpx beautifulsoup4 lxml python-dotenv alembic numpy
    fi

    log "Creating database tables..."
    cd "$PROJECT_DIR"
    python3 -c "
import sys
sys.path.insert(0, 'backend')
import asyncio
from src.database.connection import engine
from src.database.models import Base
from sqlalchemy import text

async def setup():
    async with engine.begin() as conn:
        result = await conn.execute(text(\"SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')\"))
        assert result.scalar(), 'pgvector not installed'
        print('pgvector confirmed')
        await conn.run_sync(Base.metadata.create_all)
        print('Tables created')
    await engine.dispose()

asyncio.run(setup())
"

    log "Generating sample transcripts..."
    python3 scripts/generate_seed_data.py

    log "Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    npm install

    log ""
    log "Setup complete!"
    log ""
    info "Next steps:"
    info "  1. Edit .env and set ANTHROPIC_API_KEY"
    info "  2. Edit .env and set EDGAR_USER_AGENT to 'YourName your@email.com'"
    info "  3. Run: ./start.sh run"
}

run_app() {
    check_prereqs
    start_db

    log "Starting backend (FastAPI)..."
    cd "$BACKEND_DIR"
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!

    log "Starting frontend (Vite)..."
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!

    log ""
    log "Application running:"
    info "  Frontend: http://localhost:5173"
    info "  Backend:  http://localhost:8000"
    info "  API docs: http://localhost:8000/docs"
    log ""
    info "Press Ctrl+C to stop."

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose -f $PROJECT_DIR/docker-compose.yml stop; exit" INT TERM
    wait
}

seed_data() {
    log "Generating sample transcripts..."
    cd "$PROJECT_DIR"
    python3 scripts/generate_seed_data.py
    log "Seed data generated in data/sample_transcripts/"
    info "Start the app and call POST /api/companies/seed to load into database."
}

stop_all() {
    log "Stopping services..."
    cd "$PROJECT_DIR"
    docker compose stop 2>/dev/null || true
    pkill -f "uvicorn src.api.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    log "All services stopped."
}

case "${1:-}" in
    setup)  setup ;;
    run)    run_app ;;
    db)     check_prereqs; start_db ;;
    seed)   seed_data ;;
    stop)   stop_all ;;
    *)
        echo "Earnings Call Analyzer"
        echo ""
        echo "Usage: ./start.sh <command>"
        echo ""
        echo "Commands:"
        echo "  setup   First-time setup (install deps, create tables, generate seed data)"
        echo "  run     Start backend and frontend"
        echo "  db      Start only the database"
        echo "  seed    Generate sample transcript data"
        echo "  stop    Stop all services"
        ;;
esac
