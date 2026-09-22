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

<<<<<<< HEAD
COPY backend ./backend

RUN chmod +x backend/entrypoint.sh

EXPOSE 80

CMD ["./backend/entrypoint.sh"]
=======
RUN chmod +x entrypoint.sh

EXPOSE 80

CMD ["./entrypoint.sh"]
>>>>>>> b2f9574c1909572becef00b42b8dd7f11713c5b8
