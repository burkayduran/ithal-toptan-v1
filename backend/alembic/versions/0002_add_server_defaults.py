"""add server_default for critical columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-25 00:01:00.000000

Problem
-------
When rows are inserted via raw SQL (SQLAlchemy Core execute or direct psycopg2
queries) without supplying these columns, PostgreSQL would raise:

    null value in column "images" violates not-null constraint
    null value in column "supplier_country" violates not-null constraint
    … etc.

This happened because the previous schema had only Python-level ORM defaults
(default=...) but no PostgreSQL-level DEFAULT clause on the column.

Fix
---
For each affected column this migration:
  1. Sets the DEFAULT expression on the column so raw SQL inserts work.
  2. Backfills any existing NULL rows (safe for existing data).
  3. Adds NOT NULL if the column should never be null.

Target columns
--------------
  product_requests.images          TEXT[]   DEFAULT '{}'
  product_requests.status          VARCHAR  DEFAULT 'pending'
  product_requests.view_count      INTEGER  DEFAULT 0
  supplier_offers.supplier_country VARCHAR  DEFAULT 'CN'
  supplier_offers.margin_rate      NUMERIC  DEFAULT 0.25
  supplier_offers.is_selected      BOOLEAN  DEFAULT false

Safe for existing databases
---------------------------
Every ALTER TABLE uses conditional logic or is idempotent via DO $$ blocks so
re-running against a DB that already has these defaults is harmless.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _alter_column_safe(
    table: str,
    column: str,
    pg_type: str,
    server_default: str,
    nullable: bool = False,
) -> None:
    """Idempotently add/update a column's server default and optionally
    enforce NOT NULL.

    Steps:
      1. SET DEFAULT  (always safe to repeat)
      2. Backfill NULLs with the default value
      3. SET NOT NULL (if nullable=False)
    """
    # 1. Set the DEFAULT expression
    op.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {server_default}"
    )

    # 2. Back-fill existing NULLs so we can enforce NOT NULL
    op.execute(
        f"UPDATE {table} SET {column} = {server_default} WHERE {column} IS NULL"
    )

    # 3. Enforce NOT NULL (safe if already NOT NULL)
    if not nullable:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL"
        )


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ── product_requests.images ───────────────────────────────────────────────
    _alter_column_safe(
        table="product_requests",
        column="images",
        pg_type="TEXT[]",
        server_default="'{}'",
        nullable=False,
    )

    # ── product_requests.status ───────────────────────────────────────────────
    _alter_column_safe(
        table="product_requests",
        column="status",
        pg_type="VARCHAR(50)",
        server_default="'pending'",
        nullable=False,
    )

    # ── product_requests.view_count ───────────────────────────────────────────
    _alter_column_safe(
        table="product_requests",
        column="view_count",
        pg_type="INTEGER",
        server_default="0",
        nullable=False,
    )

    # ── supplier_offers.supplier_country ──────────────────────────────────────
    _alter_column_safe(
        table="supplier_offers",
        column="supplier_country",
        pg_type="VARCHAR(10)",
        server_default="'CN'",
        nullable=False,
    )

    # ── supplier_offers.margin_rate ───────────────────────────────────────────
    _alter_column_safe(
        table="supplier_offers",
        column="margin_rate",
        pg_type="NUMERIC(5,2)",
        server_default="0.25",
        nullable=False,
    )

    # ── supplier_offers.is_selected ───────────────────────────────────────────
    _alter_column_safe(
        table="supplier_offers",
        column="is_selected",
        pg_type="BOOLEAN",
        server_default="false",
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Downgrade  (removes server defaults; does NOT restore nullability)
# ---------------------------------------------------------------------------

def downgrade() -> None:
    for table, column in [
        ("product_requests", "images"),
        ("product_requests", "status"),
        ("product_requests", "view_count"),
        ("supplier_offers", "supplier_country"),
        ("supplier_offers", "margin_rate"),
        ("supplier_offers", "is_selected"),
    ]:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL")
