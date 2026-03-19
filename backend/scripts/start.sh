#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head 2>&1 || {
    echo "Migration failed — stamping head (tables may already exist)..."
    alembic stamp head
}

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
