from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ─── User Schemas ─────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    email_verified: bool
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Category Schemas ─────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    slug: str
    parent_id: Optional[UUID] = None
    gumruk_rate: Optional[float] = None
    is_restricted: bool = False
    icon: Optional[str] = None


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    parent_id: Optional[UUID]
    gumruk_rate: Optional[float]
    is_restricted: bool
    icon: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


# ─── ProductRequest Schemas (Kullanıcı Önerileri) ────────────────────────────

class ProductRequestCreate(BaseModel):
    """Kullanıcı ürün önerisi oluşturur"""
    title: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    reference_url: Optional[str] = None
    expected_price_try: Optional[float] = None


class ProductRequestResponse(BaseModel):
    """Kullanıcı önerisi response"""
    id: UUID
    title: str
    description: Optional[str]
    category_id: Optional[UUID]
    reference_url: Optional[str]
    expected_price_try: Optional[float]
    status: str
    created_by: Optional[UUID]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductRequestUpdate(BaseModel):
    """Admin öneriyi günceller"""
    status: Optional[str] = None  # reviewing, approved, rejected
    admin_notes: Optional[str] = None


# ─── Product Schemas (Admin Ürün Ekleme) ─────────────────────────────────────

class ProductCreate(BaseModel):
    """Admin direkt ürün ekler"""
    title: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    images: List[str] = []
    
    # Tedarikçi bilgileri (aynı anda girilir)
    supplier_name: Optional[str] = None
    supplier_country: str = "CN"
    alibaba_product_url: Optional[str] = None
    unit_price_usd: float
    moq: int
    lead_time_days: Optional[int] = None
    shipping_cost_usd: Optional[float] = 0
    customs_rate: Optional[float] = 0.35  # %35 (Türkiye default)
    margin_rate: float = 0.30  # %30


class ProductUpdate(BaseModel):
    """Admin ürünü günceller"""
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    images: Optional[List[str]] = None
    status: Optional[str] = None


class ProductResponse(BaseModel):
    """Ürün response (public)"""
    id: UUID
    title: str
    description: Optional[str]
    category_id: Optional[UUID]
    images: List[str]
    status: str
    view_count: int
    created_at: datetime
    activated_at: Optional[datetime]
    
    # Offer bilgileri
    moq: Optional[int] = None
    selling_price_try: Optional[float] = None
    lead_time_days: Optional[int] = None
    
    # MoQ durumu
    current_wishlist_count: Optional[int] = None
    moq_fill_percentage: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


# ─── SupplierOffer Schemas ────────────────────────────────────────────────────

class SupplierOfferCreate(BaseModel):
    request_id: UUID
    supplier_name: Optional[str] = None
    supplier_country: str = "CN"
    alibaba_product_url: Optional[str] = None
    unit_price_usd: float
    moq: int
    lead_time_days: Optional[int] = None
    shipping_cost_usd: Optional[float] = 0
    customs_rate: Optional[float] = 0.35  # %35
    margin_rate: float = 0.30  # %30
    notes: Optional[str] = None


class PriceBreakdown(BaseModel):
    """Fiyat hesaplama detayı"""
    unit_price_usd: Decimal
    unit_price_try: Decimal
    shipping_per_unit_try: Decimal
    customs_try: Decimal
    kdv_base_try: Decimal
    kdv_try: Decimal
    total_cost_try: Decimal
    margin_try: Decimal
    selling_price_try: Decimal
    usd_rate: Decimal


class SupplierOfferResponse(BaseModel):
    id: UUID
    request_id: UUID
    supplier_name: Optional[str]
    unit_price_usd: float
    moq: int
    lead_time_days: Optional[int]
    selling_price_try: Optional[float]
    is_selected: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ─── Wishlist Schemas ─────────────────────────────────────────────────────────

class WishlistAdd(BaseModel):
    request_id: UUID
    quantity: int = 1


class WishlistResponse(BaseModel):
    id: UUID
    request_id: UUID
    user_id: UUID
    quantity: int
    status: str
    joined_at: datetime
    notified_at: Optional[datetime]
    payment_deadline: Optional[datetime]
    
    # Product info
    product_title: Optional[str] = None
    product_image: Optional[str] = None
    selling_price_try: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


# ─── Payment Schemas ──────────────────────────────────────────────────────────

class PaymentInitiate(BaseModel):
    request_id: UUID


class PaymentResponse(BaseModel):
    id: UUID
    payment_page_url: Optional[str] = None
    amount_try: float
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ─── MoQ Progress Schema ──────────────────────────────────────────────────────

class MoQProgress(BaseModel):
    request_id: UUID
    current: int
    target: int
    percentage: float
    selling_price_try: Optional[float] = None
