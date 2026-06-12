#!/bin/bash
set -e

echo "=== Gov-Scheme-Navigator Backend Startup ==="

# ── Wait for PostgreSQL ──────────────────────────────────────────────────────
if [ -n "$DATABASE_URL" ]; then
    # Extract host and port from DATABASE_URL
    # Handles: postgresql+asyncpg://user:pass@host:5432/db
    DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+).*|\1|')
    DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
    DB_PORT=${DB_PORT:-5432}

    echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."
    RETRIES=30
    until nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null || [ $RETRIES -eq 0 ]; do
        echo "  PostgreSQL not ready — retrying ($RETRIES left)..."
        RETRIES=$((RETRIES - 1))
        sleep 2
    done
    if [ $RETRIES -eq 0 ]; then
        echo "ERROR: PostgreSQL did not become available. Exiting."
        exit 1
    fi
    echo "PostgreSQL is available."

    # ── Run Alembic Migrations ────────────────────────────────────────────
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete."
else
    echo "WARNING: DATABASE_URL not set — skipping DB wait and migrations."
fi

# ── Wait for Redis ───────────────────────────────────────────────────────────
if [ -n "$REDIS_URL" ]; then
    REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's|redis://([^:/]+).*|\1|')
    REDIS_PORT=$(echo "$REDIS_URL" | sed -E 's|.*:([0-9]+).*|\1|')
    REDIS_PORT=${REDIS_PORT:-6379}

    echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT ..."
    RETRIES=15
    until nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null || [ $RETRIES -eq 0 ]; do
        echo "  Redis not ready — retrying ($RETRIES left)..."
        RETRIES=$((RETRIES - 1))
        sleep 1
    done
    echo "Redis is available (or timed out — continuing anyway)."
fi

# ── Start Application ────────────────────────────────────────────────────────
echo "Starting uvicorn..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    --access-log
