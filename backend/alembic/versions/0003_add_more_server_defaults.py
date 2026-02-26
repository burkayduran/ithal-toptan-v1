"""add server_default to remaining NOT NULL columns

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-03 00:00:00.000000

Without server_default, columns that have only a Python-ORM default= succeed
when inserted via SQLAlchemy (the ORM sets the value) but fail with a NOT NULL
violation when inserted via raw SQL, a migration script, or any client that is
not aware of the application-level defaults.

This migration adds explicit DEFAULT expressions to the remaining NOT NULL
columns that were missed in 0002.

Affected tables / columns:
  users            – email_verified, is_active, is_admin, notification_pref
  categories       – is_restricted, sort_order
  wishlist_entries – quantity, status
  payments         – quantity, status
  batch_orders     – status
  notifications    – channel, status
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE users ALTER COLUMN email_verified SET DEFAULT false")
    op.execute("ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true")
    op.execute("ALTER TABLE users ALTER COLUMN is_admin SET DEFAULT false")
    op.execute(
        """ALTER TABLE users ALTER COLUMN notification_pref """
        """SET DEFAULT '{"email": true, "sms": false}'"""
    )

    # ── categories ────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE categories ALTER COLUMN is_restricted SET DEFAULT false")
    op.execute("ALTER TABLE categories ALTER COLUMN sort_order SET DEFAULT 0")

    # ── wishlist_entries ──────────────────────────────────────────────────────
    op.execute("ALTER TABLE wishlist_entries ALTER COLUMN quantity SET DEFAULT 1")
    op.execute("ALTER TABLE wishlist_entries ALTER COLUMN status SET DEFAULT 'waiting'")

    # ── payments ──────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE payments ALTER COLUMN quantity SET DEFAULT 1")
    op.execute("ALTER TABLE payments ALTER COLUMN status SET DEFAULT 'pending'")

    # ── batch_orders ──────────────────────────────────────────────────────────
    op.execute("ALTER TABLE batch_orders ALTER COLUMN status SET DEFAULT 'pending'")

    # ── notifications ─────────────────────────────────────────────────────────
    op.execute("ALTER TABLE notifications ALTER COLUMN channel SET DEFAULT 'email'")
    op.execute("ALTER TABLE notifications ALTER COLUMN status SET DEFAULT 'pending'")


def downgrade() -> None:
    # ── notifications ─────────────────────────────────────────────────────────
    op.execute("ALTER TABLE notifications ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE notifications ALTER COLUMN channel DROP DEFAULT")

    # ── batch_orders ──────────────────────────────────────────────────────────
    op.execute("ALTER TABLE batch_orders ALTER COLUMN status DROP DEFAULT")

    # ── payments ──────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE payments ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE payments ALTER COLUMN quantity DROP DEFAULT")

    # ── wishlist_entries ──────────────────────────────────────────────────────
    op.execute("ALTER TABLE wishlist_entries ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE wishlist_entries ALTER COLUMN quantity DROP DEFAULT")

    # ── categories ────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE categories ALTER COLUMN sort_order DROP DEFAULT")
    op.execute("ALTER TABLE categories ALTER COLUMN is_restricted DROP DEFAULT")

    # ── users ─────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE users ALTER COLUMN notification_pref DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN is_admin DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN email_verified DROP DEFAULT")
