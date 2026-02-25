"""initial schema with server_default fixes

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("phone", sa.String(20)),
        sa.Column("city", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("address", sa.Text),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("notification_pref", postgresql.JSONB, nullable=False,
                  server_default=sa.text("""'{"email": true, "sms": false}'""")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── categories ───────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id")),
        sa.Column("gumruk_rate", sa.Numeric(5, 2)),
        sa.Column("is_restricted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("icon", sa.String(50)),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── product_requests ──────────────────────────────────────────────────────
    op.create_table(
        "product_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id")),
        sa.Column("reference_url", sa.Text),
        sa.Column("images", postgresql.ARRAY(sa.Text), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expected_price_try", sa.Numeric(10, 2)),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("view_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("admin_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("moq_reached_at", sa.DateTime(timezone=True)),
        sa.Column("payment_deadline", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_product_requests_status", "product_requests", ["status"])
    op.create_index("idx_product_status_created", "product_requests", ["status", "created_at"])

    # ── supplier_offers ───────────────────────────────────────────────────────
    op.create_table(
        "supplier_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_requests.id"), nullable=False),
        sa.Column("supplier_name", sa.String(255)),
        sa.Column("supplier_country", sa.String(10), nullable=False, server_default=sa.text("'CN'")),
        sa.Column("alibaba_product_url", sa.Text),
        sa.Column("unit_price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("moq", sa.Integer, nullable=False),
        sa.Column("lead_time_days", sa.Integer),
        sa.Column("shipping_cost_usd", sa.Numeric(10, 2)),
        sa.Column("customs_rate", sa.Numeric(5, 2)),
        sa.Column("usd_rate_used", sa.Numeric(10, 4)),
        sa.Column("selling_price_try", sa.Numeric(10, 2)),
        sa.Column("margin_rate", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0.25")),
        sa.Column("is_selected", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── wishlist_entries ──────────────────────────────────────────────────────
    op.create_table(
        "wishlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_requests.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'waiting'")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.Column("payment_deadline", sa.DateTime(timezone=True)),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_wishlist_entries_request_id", "wishlist_entries", ["request_id"])
    op.create_index("ix_wishlist_entries_user_id", "wishlist_entries", ["user_id"])
    op.create_index("ix_wishlist_entries_status", "wishlist_entries", ["status"])
    op.create_index("idx_wishlist_request_status", "wishlist_entries", ["request_id", "status"])
    op.create_unique_constraint("uq_wishlist_user_request", "wishlist_entries", ["request_id", "user_id"])

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("wishlist_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wishlist_entries.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_requests.id"), nullable=False),
        sa.Column("amount_try", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("iyzico_payment_id", sa.String(100)),
        sa.Column("iyzico_token", sa.String(255)),
        sa.Column("iyzico_conversation_id", sa.String(100)),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("failure_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_request_id", "payments", ["request_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    # ── batch_orders ──────────────────────────────────────────────────────────
    op.create_table(
        "batch_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_requests.id"), nullable=False),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_offers.id"), nullable=False),
        sa.Column("total_quantity", sa.Integer, nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(10, 2)),
        sa.Column("payment_total_try", sa.Numeric(10, 2)),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("supplier_order_ref", sa.String(100)),
        sa.Column("tracking_number", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_batch_orders_status", "batch_orders", ["status"])

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_requests.id")),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default=sa.text("'email'")),
        sa.Column("subject", sa.String(255)),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_unique_constraint(
        "uq_notification_user_request_type",
        "notifications",
        ["user_id", "request_id", "type"],
    )

    # ── ALTER TABLE SET DEFAULT (explicit server_default fixes) ───────────────
    # These ensure that any rows inserted via raw SQL without explicit values
    # get sensible defaults rather than NOT NULL violations.
    op.execute("ALTER TABLE product_requests ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute("ALTER TABLE product_requests ALTER COLUMN images SET DEFAULT '{}'")
    op.execute("ALTER TABLE product_requests ALTER COLUMN view_count SET DEFAULT 0")
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN supplier_country SET DEFAULT 'CN'")
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN margin_rate SET DEFAULT 0.25")
    op.execute("ALTER TABLE supplier_offers ALTER COLUMN is_selected SET DEFAULT false")
    op.execute("ALTER TABLE wishlist_entries ALTER COLUMN quantity SET DEFAULT 1")
    op.execute("ALTER TABLE wishlist_entries ALTER COLUMN status SET DEFAULT 'waiting'")
    op.execute("ALTER TABLE notifications ALTER COLUMN channel SET DEFAULT 'email'")
    op.execute("ALTER TABLE notifications ALTER COLUMN status SET DEFAULT 'pending'")


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("batch_orders")
    op.drop_table("payments")
    op.drop_table("wishlist_entries")
    op.drop_table("supplier_offers")
    op.drop_table("product_requests")
    op.drop_table("categories")
    op.drop_table("users")
