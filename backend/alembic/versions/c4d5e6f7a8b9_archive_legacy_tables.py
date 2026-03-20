"""archive_legacy_tables

Revision ID: c4d5e6f7a8b9
Revises: b3e1a2c4d5f6
Create Date: 2026-03-20 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3e1a2c4d5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add campaign_id to notifications
    op.add_column(
        "notifications",
        sa.Column("campaign_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_notification_campaign", "notifications", "campaigns",
        ["campaign_id"], ["id"],
    )

    # 2. Drop FK from notifications.request_id (pointed to product_requests)
    op.drop_constraint("notifications_request_id_fkey", "notifications", type_="foreignkey")

    # 3. Drop FK from supplier_offers.request_id (pointed to product_requests)
    op.drop_constraint("supplier_offers_request_id_fkey", "supplier_offers", type_="foreignkey")

    # 4. Rename legacy tables (data preserved, access cut)
    op.rename_table("product_requests", "legacy_product_requests")
    op.rename_table("wishlist_entries", "legacy_wishlist_entries")
    op.rename_table("payments", "legacy_payments")
    op.rename_table("batch_orders", "legacy_batch_orders")


def downgrade() -> None:
    # Reverse renames
    op.rename_table("legacy_batch_orders", "batch_orders")
    op.rename_table("legacy_payments", "payments")
    op.rename_table("legacy_wishlist_entries", "wishlist_entries")
    op.rename_table("legacy_product_requests", "product_requests")

    # Restore FKs
    op.create_foreign_key(
        "supplier_offers_request_id_fkey", "supplier_offers", "product_requests",
        ["request_id"], ["id"],
    )
    op.create_foreign_key(
        "notifications_request_id_fkey", "notifications", "product_requests",
        ["request_id"], ["id"],
    )

    # Drop campaign_id from notifications
    op.drop_constraint("fk_notification_campaign", "notifications", type_="foreignkey")
    op.drop_column("notifications", "campaign_id")
