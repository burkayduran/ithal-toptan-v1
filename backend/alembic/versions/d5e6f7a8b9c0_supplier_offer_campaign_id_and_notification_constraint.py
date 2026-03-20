"""supplier_offer_campaign_id_and_notification_constraint

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-03-20 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- BUG 4: SupplierOffer ---
    # 1. Make request_id nullable
    op.alter_column(
        "supplier_offers",
        "request_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )

    # 2. Drop FK constraint on request_id (if it exists — may have been dropped in archive migration)
    try:
        op.drop_constraint("supplier_offers_request_id_fkey", "supplier_offers", type_="foreignkey")
    except Exception:
        pass  # Constraint may already be gone after legacy table rename

    # 3. Add campaign_id column with FK to campaigns
    op.add_column(
        "supplier_offers",
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
    )

    # --- BUG 7: Notification unique constraint ---
    op.create_unique_constraint(
        "uq_notification_user_campaign_type",
        "notifications",
        ["user_id", "campaign_id", "type"],
    )


def downgrade() -> None:
    # BUG 7 rollback
    op.drop_constraint("uq_notification_user_campaign_type", "notifications", type_="unique")

    # BUG 4 rollback
    op.drop_column("supplier_offers", "campaign_id")

    op.alter_column(
        "supplier_offers",
        "request_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
