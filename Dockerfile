# ===== Base image =====
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ===== App image (used for API, UI, and ingest) =====
FROM base AS app

# copy whole repo
COPY . /app

# make top-level package importable in any working dir
ENV PYTHONPATH=/app

# default command overridden by docker-compose
CMD ["bash","-lc","uvicorn api.main:app --host 0.0.0.0 --port 8000"]
