#!/bin/bash

set -e

echo "Running database migrations..."

cd /app

uv run --project /app/backend alembic -c /app/backend/alembic.ini upgrade head

echo "Starting FastAPI..."

exec uv run --project /app/backend uvicorn backend.main:app --host 0.0.0.0 --port 80
