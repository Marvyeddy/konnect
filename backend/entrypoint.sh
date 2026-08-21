#!/bin/bash
set -ex

# Run migrations
uv run alembic upgrade head

# Start the server
exec uv run fastapi run main.py --host 0.0.0.0 --port 80