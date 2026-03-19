"""add_new_domain_tables

Revision ID: a12fa10cc453
Revises: f2d7f66340f4
Create Date: 2026-03-19 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a12fa10cc453"
down_revision: Union[str, None] = "f2d7f66340f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── products (must come before campaigns and product_suggestions) ───────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("images", sa.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("legacy_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── suppliers ──────────────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(10), nullable=False, server_default="CN"),
        sa.Column("contact_info", sa.Text(), nullable=True),
        sa.Column("alibaba_store_url", sa.Text(), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── product_suggestions ────────────────────────────────────────────────────
    op.create_table(
        "product_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_url", sa.Text(), nullable=True),
        sa.Column("images", sa.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("expected_price_try", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("converted_product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["converted_product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_suggestions_status", "product_suggestions", ["status"])
    op.create_index("idx_suggestion_status_created", "product_suggestions", ["status", "created_at"])

    # ── campaigns (depends on products, supplier_offers) ───────────────────────
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_offer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        # Tedarikçi snapshot
        sa.Column("supplier_name_snapshot", sa.String(255), nullable=True),
        sa.Column("supplier_country_snapshot", sa.String(10), nullable=True),
        # Fiyat snapshot
        sa.Column("unit_price_usd_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column("shipping_cost_usd_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column("customs_rate_snapshot", sa.Numeric(5, 2), nullable=True),
        sa.Column("margin_rate_snapshot", sa.Numeric(5, 2), nullable=True),
        sa.Column("fx_rate_snapshot", sa.Numeric(10, 4), nullable=True),
        sa.Column("selling_price_try_snapshot", sa.Numeric(10, 2), nullable=True),
        # MOQ ve süre
        sa.Column("moq", sa.Integer(), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        # Override alanları
        sa.Column("title_override", sa.String(255), nullable=True),
        sa.Column("description_override", sa.Text(), nullable=True),
        sa.Column("images_override", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("legacy_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Zaman damgaları
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moq_reached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["selected_offer_id"], ["supplier_offers.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_index("idx_campaign_status_created", "campaigns", ["status", "created_at"])
    op.create_index("idx_campaign_product", "campaigns", ["product_id"])

    # ── campaign_participants (depends on campaigns, users) ────────────────────
    op.create_table(
        "campaign_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(20), nullable=False, server_default="joined"),
        sa.Column("unit_price_try_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_amount_try_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column("legacy_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_participant_campaign_user"),
    )
    op.create_index("ix_campaign_participants_status", "campaign_participants", ["status"])
    op.create_index("idx_participant_campaign_status", "campaign_participants", ["campaign_id", "status"])

    # ── payment_transactions (depends on campaign_participants, campaigns, users)
    op.create_table(
        "payment_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_try", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unit_price_try_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column("fx_rate_snapshot", sa.Numeric(10, 4), nullable=True),
        sa.Column("provider", sa.String(30), nullable=False, server_default="iyzico"),
        sa.Column("provider_payment_id", sa.String(100), nullable=True),
        sa.Column("provider_token", sa.String(255), nullable=True),
        sa.Column("provider_conversation_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("legacy_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["campaign_participants.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])
    op.create_index("idx_payment_tx_participant", "payment_transactions", ["participant_id"])
    op.create_index("idx_payment_tx_campaign_status", "payment_transactions", ["campaign_id", "status"])

    # ── procurement_orders (depends on campaigns, supplier_offers) ─────────────
    op.create_table(
        "procurement_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_quantity", sa.Integer(), nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(12, 2), nullable=True),
        sa.Column("fx_rate_at_order", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_cost_try", sa.Numeric(12, 2), nullable=True),
        sa.Column("payment_total_try", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("supplier_order_ref", sa.String(100), nullable=True),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("legacy_batch_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["supplier_offers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procurement_orders_status", "procurement_orders", ["status"])

    # ── campaign_status_history (depends on campaigns, users) ──────────────────
    op.create_table(
        "campaign_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_status", sa.String(30), nullable=False),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_campaign_history_campaign", "campaign_status_history", ["campaign_id", "created_at"])

    # ── participant_status_history (depends on campaign_participants) ──────────
    op.create_table(
        "participant_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_status", sa.String(20), nullable=False),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["campaign_participants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_participant_history_participant", "participant_status_history", ["participant_id", "created_at"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("participant_status_history")
    op.drop_table("campaign_status_history")
    op.drop_table("procurement_orders")
    op.drop_table("payment_transactions")
    op.drop_table("campaign_participants")
    op.drop_table("campaigns")
    op.drop_table("product_suggestions")
    op.drop_table("suppliers")
    op.drop_table("products")
