import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, DateTime, Text, ARRAY, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    notification_pref: Mapped[dict] = mapped_column(
        JSONB,
        default={"email": True, "sms": False},
        server_default=text("""'{"email": true, "sms": false}'"""),
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    wishlist_entries: Mapped[List["WishlistEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ─── Category ─────────────────────────────────────────────────────────────────

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    gumruk_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    products: Mapped[List["ProductRequest"]] = relationship(back_populates="category")


# ─── ProductRequest ───────────────────────────────────────────────────────────

class ProductRequest(Base):
    __tablename__ = "product_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    reference_url: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list, server_default=text("'{}'"))
    expected_price_try: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    # Status: pending, sourcing, active, moq_reached, ordered, delivered, cancelled
    status: Mapped[str] = mapped_column(String(50), default="pending", server_default=text("'pending'"), index=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    view_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("'0'"))
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    moq_reached_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    payment_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    wishlist_entries: Mapped[List["WishlistEntry"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    supplier_offers: Mapped[List["SupplierOffer"]] = relationship(back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_product_status_created", "status", "created_at"),
    )


# ─── SupplierOffer ────────────────────────────────────────────────────────────

class SupplierOffer(Base):
    __tablename__ = "supplier_offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product_requests.id"), nullable=False)
    
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255))
    supplier_country: Mapped[str] = mapped_column(String(10), default="CN", server_default=text("'CN'"))
    alibaba_product_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Pricing
    unit_price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    moq: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)
    shipping_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    customs_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    
    # Calculated
    usd_rate_used: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    selling_price_try: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    margin_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.25, server_default=text("'0.25'"))

    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product: Mapped["ProductRequest"] = relationship(back_populates="supplier_offers")


# ─── WishlistEntry ────────────────────────────────────────────────────────────

class WishlistEntry(Base):
    __tablename__ = "wishlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product_requests.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))

    # Status: waiting, notified, paid, expired, cancelled
    status: Mapped[str] = mapped_column(String(20), default="waiting", server_default=text("'waiting'"), index=True)
    
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    payment_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="wishlist_entries")
    product: Mapped["ProductRequest"] = relationship(back_populates="wishlist_entries")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="wishlist_entry", uselist=False)

    __table_args__ = (
        Index("idx_wishlist_request_status", "request_id", "status"),
        UniqueConstraint("request_id", "user_id", name="uq_wishlist_user_request"),
    )


# ─── Payment ──────────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wishlist_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wishlist_entries.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product_requests.id"), nullable=False, index=True)
    
    amount_try: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))

    # iyzico
    iyzico_payment_id: Mapped[Optional[str]] = mapped_column(String(100))
    iyzico_token: Mapped[Optional[str]] = mapped_column(String(255))
    iyzico_conversation_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Status: pending, success, failed, refunded
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default=text("'pending'"), index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    wishlist_entry: Mapped["WishlistEntry"] = relationship(back_populates="payment")
    user: Mapped["User"] = relationship(back_populates="payments")

    __table_args__ = (
        UniqueConstraint("wishlist_entry_id", name="uq_payment_wishlist_entry"),
    )


# ─── BatchOrder ───────────────────────────────────────────────────────────────

class BatchOrder(Base):
    __tablename__ = "batch_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product_requests.id"), nullable=False)
    offer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_offers.id"), nullable=False)
    
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    payment_total_try: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    
    # Status: pending, confirmed, shipped, delivered
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default=text("'pending'"), index=True)
    supplier_order_ref: Mapped[Optional[str]] = mapped_column(String(100))
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ─── Notification ─────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", "type", name="uq_notification_user_request_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("product_requests.id"))
    
    # Type: moq_reached, payment_reminder, order_confirmed, shipped, delivered
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="email", server_default=text("'email'"))  # email, sms, push
    subject: Mapped[Optional[str]] = mapped_column(String(255))

    # Status: pending, sent, delivered, opened, clicked, failed
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default=text("'pending'"))
    
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
