FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY backend/pyproject.toml backend/uv.lock ./backend/

RUN uv sync --frozen --no-cache --no-dev --system --project ./backend

COPY backend ./backend

RUN chmod +x backend/entrypoint.sh

EXPOSE 80

CMD ["./backend/entrypoint.sh"]