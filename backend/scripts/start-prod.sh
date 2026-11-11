#!/bin/sh
set -e

# Detect alembic.ini location based on execution directory
if [ -f "alembic.ini" ]; then
    ALEMBIC_CONFIG="alembic.ini"
elif [ -f "backend/alembic.ini" ]; then
    ALEMBIC_CONFIG="backend/alembic.ini"
else
    ALEMBIC_CONFIG="alembic.ini"
fi

# Ensure PYTHONPATH contains project root and backend dir
export PYTHONPATH="${PYTHONPATH:-.}:backend"

echo "==> Running Alembic Database Migrations using $ALEMBIC_CONFIG..."
alembic -c "$ALEMBIC_CONFIG" upgrade head

echo "==> Starting FastAPI Uvicorn Server on port ${PORT:-8000}..."
exec uvicorn backend.src.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
