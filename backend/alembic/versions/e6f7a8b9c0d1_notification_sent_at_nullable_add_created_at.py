"""notification_sent_at_nullable_add_created_at

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-03-21 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Make sent_at nullable (was server_default=func.now(), now only set on actual send)
    op.alter_column(
        "notifications",
        "sent_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )

    # 2. Add created_at column for notification creation time
    op.add_column(
        "notifications",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 3. Backfill created_at from sent_at for existing rows
    op.execute("UPDATE notifications SET created_at = sent_at WHERE sent_at IS NOT NULL AND created_at IS NULL")


def downgrade() -> None:
    op.drop_column("notifications", "created_at")
    op.alter_column(
        "notifications",
        "sent_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
