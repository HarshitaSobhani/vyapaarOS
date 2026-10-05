#!/bin/sh
# Production entrypoint: apply migrations, then serve. Safe to run on every deploy (Alembic is idempotent).
set -e
alembic upgrade head
# Opt-in, one-time: set RUN_SEED=true to load demo data. The seed refuses to run on a non-empty database.
if [ "$RUN_SEED" = "true" ]; then python -m app.seed; fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
