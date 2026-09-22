FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY backend/pyproject.toml backend/uv.lock ./backend/

WORKDIR /app/backend

RUN uv sync --frozen --no-cache --no-dev

WORKDIR /app

COPY backend ./backend

RUN chmod +x backend/entrypoint.sh

EXPOSE 80

CMD ["./backend/entrypoint.sh"]