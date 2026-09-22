#!/bin/bash
set -ex

# Run migrations
uv run alembic upgrade head

# Start the server
exec uv run uvicorn main:app --host 0.0.0.0 --port 80