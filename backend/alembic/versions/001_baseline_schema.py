"""Baseline schema – create all tables

Revision ID: 001
Revises:
Create Date: 2026-02-22

Safe to run against an existing database that was bootstrapped via
``Base.metadata.create_all`` – all DDL statements use IF NOT EXISTS.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email       VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name   VARCHAR(255),
            phone       VARCHAR(20),
            city        VARCHAR(100),
            district    VARCHAR(100),
            address     TEXT,
            email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
            notification_pref JSONB NOT NULL DEFAULT '{"email": true, "sms": false}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_active_at  TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")

    # ── categories ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(100) NOT NULL,
            slug        VARCHAR(100) UNIQUE NOT NULL,
            parent_id   UUID REFERENCES categories(id),
            gumruk_rate NUMERIC(5,2),
            is_restricted BOOLEAN NOT NULL DEFAULT FALSE,
            icon        VARCHAR(50),
            sort_order  INTEGER NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── product_requests ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS product_requests (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title               VARCHAR(255) NOT NULL,
            description         TEXT,
            category_id         UUID REFERENCES categories(id),
            reference_url       TEXT,
            images              TEXT[] NOT NULL DEFAULT '{}',
            expected_price_try  NUMERIC(10,2),
            status              VARCHAR(50) NOT NULL DEFAULT 'pending',
            created_by          UUID REFERENCES users(id),
            view_count          INTEGER NOT NULL DEFAULT 0,
            admin_notes         TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            activated_at        TIMESTAMPTZ,
            moq_reached_at      TIMESTAMPTZ,
            payment_deadline    TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_requests_status ON product_requests (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_product_status_created ON product_requests (status, created_at)")

    # ── supplier_offers ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS supplier_offers (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id          UUID NOT NULL REFERENCES product_requests(id),
            supplier_name       VARCHAR(255),
            supplier_country    VARCHAR(10) NOT NULL DEFAULT 'CN',
            alibaba_product_url TEXT,
            unit_price_usd      NUMERIC(10,2) NOT NULL,
            moq                 INTEGER NOT NULL,
            lead_time_days      INTEGER,
            shipping_cost_usd   NUMERIC(10,2),
            customs_rate        NUMERIC(5,2),
            usd_rate_used       NUMERIC(10,4),
            selling_price_try   NUMERIC(10,2),
            margin_rate         NUMERIC(5,2) NOT NULL DEFAULT 0.25,
            is_selected         BOOLEAN NOT NULL DEFAULT FALSE,
            notes               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ── wishlist_entries ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS wishlist_entries (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id       UUID NOT NULL REFERENCES product_requests(id),
            user_id          UUID NOT NULL REFERENCES users(id),
            quantity         INTEGER NOT NULL DEFAULT 1,
            status           VARCHAR(20) NOT NULL DEFAULT 'waiting',
            joined_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            notified_at      TIMESTAMPTZ,
            payment_deadline TIMESTAMPTZ,
            paid_at          TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_wishlist_entries_request_id ON wishlist_entries (request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_wishlist_entries_user_id    ON wishlist_entries (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_wishlist_entries_status     ON wishlist_entries (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_request_status    ON wishlist_entries (request_id, status)")

    # ── payments ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            wishlist_entry_id         UUID NOT NULL REFERENCES wishlist_entries(id),
            user_id                   UUID NOT NULL REFERENCES users(id),
            request_id                UUID NOT NULL REFERENCES product_requests(id),
            amount_try                NUMERIC(10,2) NOT NULL,
            quantity                  INTEGER NOT NULL DEFAULT 1,
            iyzico_payment_id         VARCHAR(100),
            iyzico_token              VARCHAR(255),
            iyzico_conversation_id    VARCHAR(100),
            status                    VARCHAR(20) NOT NULL DEFAULT 'pending',
            failure_reason            TEXT,
            created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            paid_at                   TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_user_id    ON payments (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_request_id ON payments (request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_payments_status     ON payments (status)")

    # ── batch_orders ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS batch_orders (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id          UUID NOT NULL REFERENCES product_requests(id),
            offer_id            UUID NOT NULL REFERENCES supplier_offers(id),
            total_quantity      INTEGER NOT NULL,
            total_cost_usd      NUMERIC(10,2),
            payment_total_try   NUMERIC(10,2),
            status              VARCHAR(30) NOT NULL DEFAULT 'pending',
            supplier_order_ref  VARCHAR(100),
            tracking_number     VARCHAR(100),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delivered_at        TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_batch_orders_status ON batch_orders (status)")

    # ── notifications ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users(id),
            request_id  UUID REFERENCES product_requests(id),
            type        VARCHAR(50) NOT NULL,
            channel     VARCHAR(20) NOT NULL DEFAULT 'email',
            subject     VARCHAR(255),
            status      VARCHAR(20) NOT NULL DEFAULT 'pending',
            sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            opened_at   TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notifications")
    op.execute("DROP TABLE IF EXISTS batch_orders")
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("DROP TABLE IF EXISTS wishlist_entries")
    op.execute("DROP TABLE IF EXISTS supplier_offers")
    op.execute("DROP TABLE IF EXISTS product_requests")
    op.execute("DROP TABLE IF EXISTS categories")
    op.execute("DROP TABLE IF EXISTS users")
