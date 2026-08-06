FROM python:3.13-slim

WORKDIR /backend

ENV PYTHONPATH=/backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --no-dev

COPY . .

RUN chmod +x /backend/entrypoint.sh

EXPOSE 80

CMD ["bash", "/backend/entrypoint.sh"]