#!/bin/bash

set -e

echo "Running database migrations..."

alembic -c /app/backend/alembic.ini upgrade head

echo "Starting FastAPI..."

exec uvicorn backend.main:app --host 0.0.0.0 --port 80
