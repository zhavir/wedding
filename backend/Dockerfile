FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.15.0-slim AS base
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
# Point psycopg's bundled OpenSSL at Debian's CA bundle for sslrootcert=system.
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
WORKDIR /app
COPY pyproject.toml uv.lock* ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
COPY frontend/static/calendar backend/app/assets
RUN if [ ! -f uv.lock ]; then uv lock; fi \
    && uv sync --frozen --package wedding-api --no-dev --no-editable
COPY scripts scripts
COPY alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test
RUN apt-get update && apt-get install -y --no-install-recommends jq && rm -rf /var/lib/apt/lists/*
RUN uv sync --frozen --all-packages --all-groups --no-editable
COPY .github/rulesets .github/rulesets
COPY backend/tests backend/tests
COPY frontend/static/calendar frontend/static/calendar
CMD ["pytest", "backend/tests", "-q"]

FROM base AS lambda
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=8000 AWS_LWA_READINESS_CHECK_PATH=/api/health
# Use the same ASGI server locally and on Lambda. The adapter handles Lambda events.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
