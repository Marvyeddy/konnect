#!/bin/bash

set -ex

uv run alembic upgrade head

uv run alembic -x db=test upgrade head

exec uv run uvicorn backend.main:app --host 0.0.0.0 --port 80