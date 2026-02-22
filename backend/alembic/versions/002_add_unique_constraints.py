"""Add unique constraints for wishlist and notifications

Revision ID: 002
Revises: 001
Create Date: 2026-02-22

Adds:
  - uq_wishlist_user_request     on wishlist_entries(request_id, user_id)
  - uq_notification_user_request_type on notifications(user_id, request_id, type)

Both operations use DO $$ ... EXCEPTION WHEN duplicate_object ... END $$
so they are safe to run on an existing database that already has the constraints.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint on wishlist_entries(request_id, user_id)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE wishlist_entries
                ADD CONSTRAINT uq_wishlist_user_request UNIQUE (request_id, user_id);
        EXCEPTION
            WHEN duplicate_object THEN
                RAISE NOTICE 'uq_wishlist_user_request already exists, skipping';
        END $$
    """)

    # Add unique constraint on notifications(user_id, request_id, type)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE notifications
                ADD CONSTRAINT uq_notification_user_request_type
                    UNIQUE (user_id, request_id, type);
        EXCEPTION
            WHEN duplicate_object THEN
                RAISE NOTICE 'uq_notification_user_request_type already exists, skipping';
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE notifications
            DROP CONSTRAINT IF EXISTS uq_notification_user_request_type
    """)
    op.execute("""
        ALTER TABLE wishlist_entries
            DROP CONSTRAINT IF EXISTS uq_wishlist_user_request
    """)
