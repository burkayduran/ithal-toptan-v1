import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, DateTime, Text, ARRAY, Index, UniqueConstraint
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
    
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    notification_pref: Mapped[dict] = mapped_column(JSONB, default={"email": True, "sms": False})
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    wishlist_entries: Mapped[List["WishlistEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    campaign_participants: Mapped[List["CampaignParticipant"]] = relationship("CampaignParticipant")
    suggestions: Mapped[List["ProductSuggestion"]] = relationship("ProductSuggestion")


# ─── Category ─────────────────────────────────────────────────────────────────

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    gumruk_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    products: Mapped[List["ProductRequest"]] = relationship(back_populates="category")
    catalog_products: Mapped[List["Product"]] = relationship("Product", foreign_keys="[Product.category_id]")


# ─── ProductRequest ───────────────────────────────────────────────────────────

class ProductRequest(Base):
    __tablename__ = "legacy_product_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    reference_url: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    expected_price_try: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    
    # Status: pending, sourcing, active, moq_reached, payment_collecting, ordered, delivered, cancelled
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    view_count: Mapped[int] = mapped_column(Integer, default=0)
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
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("legacy_product_requests.id"), nullable=False)
    
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255))
    supplier_country: Mapped[str] = mapped_column(String(10), default="CN")
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
    margin_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.25)
    
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product: Mapped["ProductRequest"] = relationship(back_populates="supplier_offers")


# ─── WishlistEntry ────────────────────────────────────────────────────────────

class WishlistEntry(Base):
    __tablename__ = "legacy_wishlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("legacy_product_requests.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    
    # Status: waiting, notified, paid, expired, cancelled
    status: Mapped[str] = mapped_column(String(20), default="waiting", index=True)
    
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
    __tablename__ = "legacy_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wishlist_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("legacy_wishlist_entries.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("legacy_product_requests.id"), nullable=False, index=True)
    
    amount_try: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    
    # iyzico
    iyzico_payment_id: Mapped[Optional[str]] = mapped_column(String(100))
    iyzico_token: Mapped[Optional[str]] = mapped_column(String(255))
    iyzico_conversation_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Status: pending, success, failed, refunded
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    wishlist_entry: Mapped["WishlistEntry"] = relationship(back_populates="payment")
    user: Mapped["User"] = relationship(back_populates="payments")


# ─── BatchOrder ───────────────────────────────────────────────────────────────

class BatchOrder(Base):
    __tablename__ = "legacy_batch_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("legacy_product_requests.id"), nullable=False)
    offer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_offers.id"), nullable=False)
    
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    payment_total_try: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    
    # Status: pending, confirmed, shipped, delivered
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
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
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"))

    # Type: moq_reached, payment_reminder, order_confirmed, shipped, delivered
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="email")  # email, sms, push
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Status: pending, sent, delivered, opened, clicked, failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ══════════════════════════════════════════════════════════════════════════════
# NEW DOMAIN MODELS (Faz 1)
# Mevcut 8 tablo olduğu gibi kalıyor. Aşağıdaki tablolar YANINA ekleniyor.
# ══════════════════════════════════════════════════════════════════════════════


# ─── NEW DOMAIN: ProductSuggestion ───────────────────────────────────────────

class ProductSuggestion(Base):
    """
    Intake layer — müşteri ürün önerileri.
    Mevcut product_requests'teki suggestion rolünü devralır.
    Operasyonel kampanyadan tamamen ayrı tutulur.
    """
    __tablename__ = "product_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    reference_url: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)
    expected_price_try: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    # Status: pending → reviewing → approved / rejected
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Hangi kullanıcı önerdi
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Eğer bu öneriden bir product oluşturulduysa referans
    converted_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_suggestion_status_created", "status", "created_at"),
    )


# ─── NEW DOMAIN: Product ─────────────────────────────────────────────────────

class Product(Base):
    """
    Catalog layer — canonical ürün kaydı.
    Kampanyadan bağımsız temel ürün bilgisi.
    Bir üründen zaman içinde birden fazla campaign açılabilir.
    """
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    images: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list)

    # Admin tarafından oluşturuldu
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Eski product_requests kaydına referans (backfill sonrası doldurulacak)
    legacy_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaigns: Mapped[List["Campaign"]] = relationship(back_populates="product")


# ─── NEW DOMAIN: Supplier ────────────────────────────────────────────────────

class Supplier(Base):
    """
    Catalog layer — tedarikçi ana kaydı.
    Offer satırlarından ayrıştırılmış, normalize edilmiş tedarikçi.
    """
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(10), default="CN")
    contact_info: Mapped[Optional[str]] = mapped_column(Text)
    alibaba_store_url: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))  # 0.00 - 5.00
    notes: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── NEW DOMAIN: Campaign ────────────────────────────────────────────────────

class Campaign(Base):
    """
    Commerce layer — group-buy çekirdeği.
    Fiyat, kur, marj ve tedarik bilgileri snapshot olarak saklanır.
    selected_offer_id ile baz alınan teklif kampanya bağlamında tutulur.
    """
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    selected_offer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_offers.id"))

    # Status: draft → active → moq_reached → payment_collecting → ordered → delivered / cancelled
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)

    # ── Snapshot alanları (campaign açılışında kilitlenir) ──
    # Tedarikçi snapshot
    supplier_name_snapshot: Mapped[Optional[str]] = mapped_column(String(255))
    supplier_country_snapshot: Mapped[Optional[str]] = mapped_column(String(10))
    alibaba_product_url_snapshot: Mapped[Optional[str]] = mapped_column(Text)

    # Fiyat snapshot
    unit_price_usd_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    shipping_cost_usd_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    customs_rate_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    margin_rate_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    fx_rate_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    selling_price_try_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    # MOQ ve süre
    moq: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Ürün görünürlük alanları (kampanya kapsamında override edilebilir)
    title_override: Mapped[Optional[str]] = mapped_column(String(255))
    description_override: Mapped[Optional[str]] = mapped_column(Text)
    images_override: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))

    view_count: Mapped[int] = mapped_column(Integer, default=0)

    # Eski product_requests kaydına referans (backfill sonrası doldurulacak)
    legacy_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Zaman damgaları
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    moq_reached_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    payment_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ordered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="campaigns")
    participants: Mapped[List["CampaignParticipant"]] = relationship(back_populates="campaign")
    status_history: Mapped[List["CampaignStatusHistory"]] = relationship(back_populates="campaign")

    __table_args__ = (
        Index("idx_campaign_status_created", "status", "created_at"),
        Index("idx_campaign_product", "product_id"),
    )


# ─── NEW DOMAIN: CampaignParticipant ─────────────────────────────────────────

class CampaignParticipant(Base):
    """
    Commerce layer — kampanyaya katılan kullanıcı.
    UNIQUE(campaign_id, user_id) — bir kullanıcı aynı kampanyada tek satır.
    Katılım anındaki fiyat snapshot olarak saklanır.
    """
    __tablename__ = "campaign_participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Status: joined → invited → paid → expired / cancelled
    status: Mapped[str] = mapped_column(String(20), default="joined", index=True)

    # Fiyat snapshot (katılım anında kampanyadan kopyalanır)
    unit_price_try_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    total_amount_try_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    # Eski wishlist_entry kaydına referans (backfill sonrası)
    legacy_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    payment_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="participants")
    payment_transactions: Mapped[List["PaymentTransaction"]] = relationship(back_populates="participant")
    status_history: Mapped[List["ParticipantStatusHistory"]] = relationship(back_populates="participant")

    __table_args__ = (
        UniqueConstraint("campaign_id", "user_id", name="uq_participant_campaign_user"),
        Index("idx_participant_campaign_status", "campaign_id", "status"),
    )


# ─── NEW DOMAIN: PaymentTransaction ──────────────────────────────────────────

class PaymentTransaction(Base):
    """
    Commerce layer — ödeme attempt/transaction kaydı.
    Bir participant için birden çok attempt olabilir; status=success için tek kayıt.
    """
    __tablename__ = "payment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaign_participants.id"), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    amount_try: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Snapshot — ödeme anındaki fiyat bilgisi
    unit_price_try_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    fx_rate_snapshot: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    # iyzico alanları
    provider: Mapped[str] = mapped_column(String(30), default="iyzico")
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(100))
    provider_token: Mapped[Optional[str]] = mapped_column(String(255))
    provider_conversation_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Status: pending → success / failed / refunded
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Idempotency key — aynı attempt tekrar edilmesin
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), unique=True)

    # Eski payment kaydına referans
    legacy_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    participant: Mapped["CampaignParticipant"] = relationship(back_populates="payment_transactions")

    __table_args__ = (
        Index("idx_payment_tx_participant", "participant_id"),
        Index("idx_payment_tx_campaign_status", "campaign_id", "status"),
    )


# ─── NEW DOMAIN: ProcurementOrder ────────────────────────────────────────────

class ProcurementOrder(Base):
    """
    Commerce layer — tedarikçiye verilen toplu sipariş.
    Sipariş anındaki maliyet ve kur bilgisi snapshot olarak saklanır.
    """
    __tablename__ = "procurement_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    offer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_offers.id"), nullable=False)

    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Maliyet snapshot
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    fx_rate_at_order: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    total_cost_try: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    payment_total_try: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))

    # Status: pending → confirmed → shipped → delivered / cancelled
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    supplier_order_ref: Mapped[Optional[str]] = mapped_column(String(100))
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Eski batch_order referansı
    legacy_batch_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ─── NEW DOMAIN: CampaignStatusHistory ───────────────────────────────────────

class CampaignStatusHistory(Base):
    """
    Analytics layer — kampanya status geçiş kaydı.
    Her geçiş bir satır olarak saklanır: eski → yeni status, neden, kim yaptı.
    """
    __tablename__ = "campaign_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)

    old_status: Mapped[str] = mapped_column(String(30), nullable=False)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="status_history")

    __table_args__ = (
        Index("idx_campaign_history_campaign", "campaign_id", "created_at"),
    )


# ─── NEW DOMAIN: ParticipantStatusHistory ────────────────────────────────────

class ParticipantStatusHistory(Base):
    """
    Analytics layer — katılımcı status geçiş kaydı.
    joined → invited → paid gibi akışı izlenebilir yapar.
    """
    __tablename__ = "participant_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaign_participants.id"), nullable=False)

    old_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    participant: Mapped["CampaignParticipant"] = relationship(back_populates="status_history")

    __table_args__ = (
        Index("idx_participant_history_participant", "participant_id", "created_at"),
    )
