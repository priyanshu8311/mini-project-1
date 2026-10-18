#!/bin/sh
set -e

echo "==> Running Alembic Database Migrations..."
alembic upgrade head

echo "==> Starting FastAPI Uvicorn Server..."
exec uvicorn backend.src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WEB_CONCURRENCY:-4}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
