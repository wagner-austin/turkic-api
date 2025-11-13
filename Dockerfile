# syntax=docker/dockerfile:1.6

# ---------- Builder: resolve and install dependencies into a venv ----------
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential curl git libicu-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip poetry poetry-plugin-export

WORKDIR /app

# Export locked runtime dependencies and install into /opt/venv using pip
COPY pyproject.toml poetry.lock ./
RUN poetry export --only main --without-hashes -f requirements.txt -o requirements.txt \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/python -c "import hypercorn, rq; print('deps ok')"

# ---------- Runtime: minimal image with ICU runtime + venv ----------
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

# Install ICU runtime libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends libicu72 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application code
COPY api api
COPY core core

EXPOSE 8000

# Default command: run the API via Hypercorn app factory
CMD ["hypercorn", "api.main:create_app()", "--bind", "[::]:8000"]
