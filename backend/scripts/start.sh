#!/bin/sh
set -e

echo "=== Running database migrations ==="
# If this is a fresh DB, alembic upgrade head creates all tables.
# If the DB already has all tables (from a previous run), this is a no-op.
# If you are pointing at a pre-existing DB that has no alembic_version table,
# run manually: alembic stamp head — then restart.
alembic upgrade head

echo "=== Starting application ==="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
