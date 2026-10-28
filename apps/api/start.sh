#!/bin/sh
set -e

echo "=========================================================="
echo " Starting SyntaxLens Research Platform Backend (Render)"
echo "=========================================================="

# Run database migrations
echo "==> Running Alembic Database Migrations..."
if alembic upgrade head; then
    echo "==> Migrations applied successfully."
else
    echo "==> Alembic upgrade had a non-zero exit; attempting fallback table creation..."
    python -c "from app.core.database import Base, sync_engine; Base.metadata.create_all(bind=sync_engine)" || true
fi

# Seed baseline data (idempotent, ON CONFLICT DO NOTHING)
echo "==> Ensuring default research rubrics and seed accounts are initialized..."
python -m app.seed || echo "==> Seed skipped or already provisioned."

# Determine dynamic port (Render injects $PORT, defaults to 8000)
PORT="${PORT:-8000}"
echo "==> Launching uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
