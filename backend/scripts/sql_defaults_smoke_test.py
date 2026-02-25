#!/usr/bin/env python3
"""sql_defaults_smoke_test.py

Smoke-test that PostgreSQL server_default values are correctly set for the
critical columns in product_requests and supplier_offers.

The test inserts rows using **raw SQL / SQLAlchemy Core execute** — i.e. it
deliberately omits the columns that should fall back to server defaults — and
then verifies the resulting values.

Usage
-----
    python backend/scripts/sql_defaults_smoke_test.py

Environment variables
---------------------
    DATABASE_URL  — PostgreSQL connection string (sync psycopg2 or asyncpg;
                    asyncpg URLs are automatically converted to psycopg2).
                    Falls back to the docker-compose default if not set.

Exit codes
----------
    0  — all assertions passed
    1  — one or more assertions failed
"""
from __future__ import annotations

import os
import re
import sys
import traceback
import uuid
from decimal import Decimal

# ---------------------------------------------------------------------------
# Dependency setup
# ---------------------------------------------------------------------------
try:
    import sqlalchemy
except ImportError:
    print("[SKIP] sqlalchemy not installed — run: pip install sqlalchemy psycopg2-binary")
    sys.exit(0)

from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# DB URL
# ---------------------------------------------------------------------------
_DEFAULT_DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/toplu_alisveris"


def _sync_url(url: str) -> str:
    """Convert asyncpg URL → psycopg2 URL if needed."""
    return re.sub(r"postgresql\+asyncpg", "postgresql+psycopg2", url)


DATABASE_URL = _sync_url(os.environ.get("DATABASE_URL", _DEFAULT_DB_URL))

# ---------------------------------------------------------------------------
# Test runner helpers
# ---------------------------------------------------------------------------
_failures: list[str] = []
_passes: int = 0


def _check(label: str, got, expected) -> None:
    global _passes
    if got == expected:
        print(f"  [PASS] {label}: {got!r}")
        _passes += 1
    else:
        msg = f"  [FAIL] {label}: expected {expected!r}, got {got!r}"
        print(msg)
        _failures.append(msg)


def _check_not_none(label: str, got) -> None:
    global _passes
    if got is not None:
        print(f"  [PASS] {label}: {got!r} (not None)")
        _passes += 1
    else:
        msg = f"  [FAIL] {label}: expected non-None value, got None"
        print(msg)
        _failures.append(msg)


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

def run_tests(conn) -> None:
    # ── Unique test run marker ──────────────────────────────────────────────
    run_id = str(uuid.uuid4())
    print(f"\nTest run ID: {run_id}\n")

    # ── 1. Insert a ProductRequest with minimal columns ─────────────────────
    print("=== ProductRequest (raw SQL, no images / status / view_count) ===")

    pr_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO product_requests (id, title)
        VALUES (:id, :title)
    """), {"id": pr_id, "title": f"smoke-test-{run_id}"})

    row = conn.execute(text("""
        SELECT images, status, view_count
        FROM product_requests
        WHERE id = :id
    """), {"id": pr_id}).mappings().fetchone()

    _check_not_none("images is not NULL", row["images"])
    _check("images == []", list(row["images"]), [])
    _check("status == 'pending'", row["status"], "pending")
    _check("view_count == 0", row["view_count"], 0)

    # ── 2. Insert a SupplierOffer with minimal columns ───────────────────────
    print("\n=== SupplierOffer (raw SQL, no supplier_country / margin_rate / is_selected) ===")

    so_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO supplier_offers (id, request_id, unit_price_usd, moq)
        VALUES (:id, :request_id, :unit_price_usd, :moq)
    """), {
        "id": so_id,
        "request_id": pr_id,
        "unit_price_usd": "9.99",
        "moq": 10,
    })

    row = conn.execute(text("""
        SELECT supplier_country, margin_rate, is_selected
        FROM supplier_offers
        WHERE id = :id
    """), {"id": so_id}).mappings().fetchone()

    _check("supplier_country == 'CN'", row["supplier_country"], "CN")
    _check("margin_rate == 0.25", Decimal(str(row["margin_rate"])), Decimal("0.25"))
    _check("is_selected == False", row["is_selected"], False)

    # ── 3. Cleanup ───────────────────────────────────────────────────────────
    conn.execute(text("DELETE FROM supplier_offers WHERE id = :id"), {"id": so_id})
    conn.execute(text("DELETE FROM product_requests WHERE id = :id"), {"id": pr_id})


def main() -> int:
    print(f"Connecting to: {DATABASE_URL}")
    try:
        engine = create_engine(DATABASE_URL, future=True)
        with engine.connect() as conn:
            with conn.begin():
                run_tests(conn)
                # Roll back so we leave no test data behind.
                raise Exception("__rollback__")
    except Exception as exc:
        if "__rollback__" not in str(exc):
            print(f"\n[ERROR] Unexpected exception:\n{traceback.format_exc()}")
            return 1

    print(f"\n{'='*50}")
    if _failures:
        print(f"RESULT: {len(_failures)} failure(s), {_passes} pass(es)")
        for f in _failures:
            print(f"  {f}")
        return 1
    else:
        print(f"RESULT: ALL {_passes} checks passed ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())
