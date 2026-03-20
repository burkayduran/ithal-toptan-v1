"""add_alibaba_url_snapshot_to_campaigns

Revision ID: b3e1a2c4d5f6
Revises: a12fa10cc453
Create Date: 2026-03-20 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3e1a2c4d5f6"
down_revision: Union[str, None] = "a12fa10cc453"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("alibaba_product_url_snapshot", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "alibaba_product_url_snapshot")
