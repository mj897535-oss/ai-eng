#!/bin/sh

echo "=========================================================="
echo " Starting SyntaxLens Research Platform Backend (Render)"
echo "=========================================================="

# Check if DATABASE_URL is unset or localhost and postgres is unreachable
if [ -z "$DATABASE_URL" ] || echo "$DATABASE_URL" | grep -q "localhost:5432"; then
    echo "==> Checking database availability..."
    if ! python -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('localhost', 5432)); s.close()" 2>/dev/null; then
        echo "==> PostgreSQL not detected on localhost:5432; configuring local SQLite database for standalone mode..."
        export DATABASE_URL="sqlite+aiosqlite:////app/syntaxlens.db"
        export DATABASE_URL_SYNC="sqlite:////app/syntaxlens.db"
    fi
fi

# Run database setup
echo "==> Initializing Database..."
if echo "$DATABASE_URL" | grep -q "postgresql"; then
    echo "==> Running Alembic Database Migrations on PostgreSQL..."
    alembic upgrade head || {
        echo "==> Alembic upgrade fallback; ensuring tables exist via models..."
        python -c "from app.models import Base; from app.core.database import sync_engine; Base.metadata.create_all(bind=sync_engine)" || true
    }
else
    echo "==> SQLite detected. Initializing tables via SQLAlchemy..."
    python -c "from app.models import Base; from app.core.database import sync_engine; Base.metadata.create_all(bind=sync_engine)" || true
fi

# Seed baseline data (idempotent, ON CONFLICT DO NOTHING)
echo "==> Ensuring default research rubrics and seed accounts are initialized..."
python -m app.seed || echo "==> Seed skipped or already provisioned."

# Determine dynamic port (Render injects $PORT, defaults to 8000)
PORT="${PORT:-8000}"
echo "==> Launching uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
