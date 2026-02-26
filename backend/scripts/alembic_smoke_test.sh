#!/usr/bin/env bash
# =============================================================================
# Alembic smoke test
# =============================================================================
# Creates a throwaway PostgreSQL database, runs `alembic upgrade head`,
# verifies server_default values via raw SQL, then drops the database.
#
# Usage (from repo root or backend/):
#   bash backend/scripts/alembic_smoke_test.sh
#
# Environment overrides (all optional – defaults shown):
#   PGHOST=localhost  PGPORT=5432  PGUSER=postgres  PGPASSWORD=postgres
#   REDIS_URL=redis://localhost:6379/15
#
# Also demonstrates that ALGORITHM=HS256 in the environment is silently
# tolerated (the previous extra_forbidden blocker is fixed).
# =============================================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"
TEST_DB="alembic_smoke_$$"          # unique name prevents collisions

# Locate the backend/ directory regardless of where the script is called from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PGPASSWORD

# ── Cleanup trap ──────────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "[CLEANUP] Dropping test database '${TEST_DB}' …"
    dropdb --if-exists -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${TEST_DB}" 2>/dev/null || true
}
trap cleanup EXIT

# ── Step 1: fresh database ────────────────────────────────────────────────────
echo "=== [1/5] Creating fresh database '${TEST_DB}' ==="
createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${TEST_DB}"

# ── Step 2: set env vars for Alembic ─────────────────────────────────────────
echo "=== [2/5] Configuring environment ==="
export DATABASE_URL="postgresql+asyncpg://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${TEST_DB}"
export SECRET_KEY="smoke-test-secret-key-do-not-use-in-production"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/15}"
export EMAIL_PROVIDER="fake"

# Demonstrate that ALGORITHM=HS256 in .env no longer crashes Settings
# (extra="ignore" was the fix; extra_forbidden was the previous blocker).
export ALGORITHM="HS256"

echo "  DATABASE_URL=${DATABASE_URL}"
echo "  ALGORITHM=${ALGORITHM}  (extra env var – should be silently accepted)"

# ── Step 3: alembic upgrade head ──────────────────────────────────────────────
echo "=== [3/5] Running: alembic upgrade head ==="
cd "${BACKEND_DIR}"
alembic upgrade head
echo "  alembic upgrade head: exit 0 ✓"

# ── Step 4: verify server_defaults via raw SQL ────────────────────────────────
echo "=== [4/5] Verifying server_default values via raw SQL ==="

# Use a sync connection string for psql
SYNC_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${TEST_DB}"

psql "${SYNC_URL}" <<'SQL'
\set ON_ERROR_STOP on

-- ── product_requests: insert only required column ───────────────────────────
INSERT INTO product_requests (title) VALUES ('smoke_defaults_pr');

DO $$
DECLARE
  r RECORD;
BEGIN
  SELECT status, view_count, images
    INTO r
    FROM product_requests
   WHERE title = 'smoke_defaults_pr';

  ASSERT r.status    = 'pending',  'status default wrong: ' || r.status;
  ASSERT r.view_count = 0,         'view_count default wrong: ' || r.view_count;
  ASSERT r.images    = '{}',       'images default wrong';
  RAISE NOTICE 'product_requests defaults OK (status=%, view_count=%, images={})',
        r.status, r.view_count;
END $$;

-- ── supplier_offers: insert only required columns ───────────────────────────
INSERT INTO supplier_offers (request_id, unit_price_usd, moq)
SELECT id, 9.99, 5
  FROM product_requests
 WHERE title = 'smoke_defaults_pr';

DO $$
DECLARE
  r RECORD;
BEGIN
  SELECT supplier_country, margin_rate::numeric, is_selected
    INTO r
    FROM supplier_offers
   WHERE request_id = (SELECT id FROM product_requests WHERE title = 'smoke_defaults_pr');

  ASSERT r.supplier_country = 'CN',    'supplier_country default wrong: ' || r.supplier_country;
  ASSERT r.margin_rate      = 0.25,    'margin_rate default wrong: ' || r.margin_rate;
  ASSERT r.is_selected      = false,   'is_selected default wrong';
  RAISE NOTICE 'supplier_offers defaults OK (country=%, margin=%, selected=%)',
        r.supplier_country, r.margin_rate, r.is_selected;
END $$;
SQL

echo "  Raw SQL server_default assertions: all passed ✓"

# ── Step 5: confirm alembic_version table has expected head ──────────────────
echo "=== [5/5] Confirming alembic_version ==="
REVISION=$(psql "${SYNC_URL}" -t -c "SELECT version_num FROM alembic_version;" | tr -d '[:space:]')
echo "  Current revision: ${REVISION}"

# Acceptable heads are 0001 (initial) or 0002 (server defaults added on top)
if [[ "${REVISION}" == "0001" || "${REVISION}" == "0002" ]]; then
    echo "  alembic_version is at expected head ✓"
else
    echo "  UNEXPECTED revision '${REVISION}'" >&2
    exit 1
fi

echo ""
echo "=== ALL SMOKE TESTS PASSED ✓ ==="
