"""add unique constraint on payments.wishlist_entry_id

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-04 00:00:00.000000

A payment belongs to exactly one wishlist_entry (1:1).  Without a DB-level
unique constraint a bug or race condition could create two Payment rows for the
same WishlistEntry, leading to double-charges.

This migration adds a UNIQUE constraint on payments.wishlist_entry_id so the
DB enforces the invariant regardless of the application layer.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_payment_wishlist_entry",
        "payments",
        ["wishlist_entry_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_payment_wishlist_entry",
        "payments",
        type_="unique",
    )
