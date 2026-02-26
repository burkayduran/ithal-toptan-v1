"""add server_default to columns missing DB-level defaults

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000

Without server_default, columns that have only a Python-ORM default= will
succeed when inserted via SQLAlchemy (Python supplies the value) but fail
with a NOT NULL violation when inserted via raw SQL or another client that
does not know about the application defaults.

This migration adds explicit DEFAULT expressions to the affected columns so
that raw-SQL inserts work correctly on existing databases that were created
by SQLAlchemy's create_all() rather than Alembic.

Affected tables / columns:
  product_requests  – status, images, view_count
  supplier_offers   – supplier_country, margin_rate, is_selected
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # product_requests
    op.execute("ALTER TABLE product_requests ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("ALTER TABLE product_requests ALTER COLUMN images SET DEFAULT '{}'")
    op.execute("ALTER TABLE product_requests ALTER COLUMN view_count SET DEFAULT 0")

    # supplier_offers
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN supplier_country SET DEFAULT 'CN'")
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN margin_rate SET DEFAULT 0.25")
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN is_selected SET DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE product_requests ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE product_requests ALTER COLUMN images DROP DEFAULT")
    op.execute("ALTER TABLE product_requests ALTER COLUMN view_count DROP DEFAULT")

    op.execute("ALTER TABLE supplier_offers ALTER COLUMN supplier_country DROP DEFAULT")
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN margin_rate DROP DEFAULT")
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN is_selected DROP DEFAULT")
