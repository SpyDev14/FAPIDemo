FROM python:3.13.8-slim-bookworm AS base

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

# ---- Dev ----
FROM base AS dev
RUN uv sync --frozen

# не добавляйте .env, envars только через docker-compose env_file: [.env]
# чтобы не утекал в образ
COPY alembic.ini .
COPY alembic .
COPY tests .
COPY app .

# ---- Prod ----
FROM base AS prod
RUN uv sync --frozen --only-group prod

# не добавляйте .env, envars только через docker-compose env_file: [.env]
# чтобы не утекал в образ
COPY alembic.ini .
COPY alembic .
COPY app .
