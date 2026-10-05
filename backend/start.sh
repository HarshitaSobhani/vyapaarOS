#!/bin/sh
# Production entrypoint: apply migrations, then serve. Safe to run on every deploy (Alembic is idempotent).
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
