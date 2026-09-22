#!/bin/bash
set -ex

# Run migrations
uv run alembic upgrade head

# Start the server
exec uvicorn backend.main:app --host 0.0.0.0 --port 80