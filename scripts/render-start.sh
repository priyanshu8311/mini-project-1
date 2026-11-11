#!/bin/sh
set -e

# Render Web Service Startup Script for Smart Inventory Backend
echo "==> Render Environment Detected: PORT=${PORT:-8000}, ENVIRONMENT=${ENVIRONMENT:-production}"

# Ensure PYTHONPATH includes root and backend
export PYTHONPATH="${PYTHONPATH:-.}:backend"

# Determine path to alembic.ini
if [ -f "backend/alembic.ini" ]; then
    ALEMBIC_CONFIG="backend/alembic.ini"
elif [ -f "alembic.ini" ]; then
    ALEMBIC_CONFIG="alembic.ini"
else
    ALEMBIC_CONFIG="backend/alembic.ini"
fi

echo "==> Executing Alembic database migrations ($ALEMBIC_CONFIG)..."
alembic -c "$ALEMBIC_CONFIG" upgrade head

echo "==> Starting Uvicorn server on 0.0.0.0:${PORT:-8000}..."
exec uvicorn backend.src.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers \
    --forwarded-allow-ips='*'

