"""
V2 Pydantic schemas — new domain tables.
Mevcut schemas.py'ye dokunulmaz.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Status Literals ───────────────────────────────────────────────────────

CampaignStatus = Literal[
    "draft", "active", "moq_reached", "payment_collecting",
    "ordered", "delivered", "cancelled",
]
SuggestionStatus = Literal["pending", "reviewing", "approved", "rejected"]
ParticipantStatus = Literal["joined", "invited", "paid", "expired", "cancelled"]
PaymentStageV2 = Literal[
    "campaign_active", "moq_reached", "payment_confirmed",
    "order_placed", "delivered",
]


# ── Campaign ──────────────────────────────────────────────────────────────

class CampaignResponse(BaseModel):
    id: UUID
    product_id: UUID
    title: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    images: List[str] = []
    status: str
    view_count: int = 0
    created_at: datetime
    activated_at: Optional[datetime] = None
    moq: int
    selling_price_try: Optional[float] = None
    lead_time_days: Optional[int] = None
    current_participant_count: int = 0
    moq_fill_percentage: Optional[float] = None

    model_config = {"from_attributes": True}


class PaginatedCampaignResponse(BaseModel):
    items: List[CampaignResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AdminCampaignDetailResponse(CampaignResponse):
    selected_offer_id: Optional[UUID] = None
    supplier_name_snapshot: Optional[str] = None
    supplier_country_snapshot: Optional[str] = None
    alibaba_product_url_snapshot: Optional[str] = None
    unit_price_usd_snapshot: Optional[float] = None
    shipping_cost_usd_snapshot: Optional[float] = None
    customs_rate_snapshot: Optional[float] = None
    margin_rate_snapshot: Optional[float] = None
    fx_rate_snapshot: Optional[float] = None
    moq_reached_at: Optional[datetime] = None
    payment_deadline: Optional[datetime] = None
    ordered_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class CampaignCreatePayload(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    images: List[str] = []
    supplier_name: Optional[str] = None
    supplier_country: str = "CN"
    alibaba_product_url: Optional[str] = None
    unit_price_usd: float = Field(gt=0)
    moq: int = Field(ge=1)
    lead_time_days: Optional[int] = None
    shipping_cost_usd: float = 0
    customs_rate: float = 0.35
    margin_rate: float = 0.30
    from_suggestion_id: Optional[UUID] = None


class CampaignUpdatePayload(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    images: Optional[List[str]] = None
    status: Optional[CampaignStatus] = None
    supplier_name: Optional[str] = None
    supplier_country: Optional[str] = None
    alibaba_product_url: Optional[str] = None
    unit_price_usd: Optional[float] = None
    moq: Optional[int] = None
    lead_time_days: Optional[int] = None
    shipping_cost_usd: Optional[float] = None
    customs_rate: Optional[float] = None
    margin_rate: Optional[float] = None


# ── Suggestion ────────────────────────────────────────────────────────────

class SuggestionCreatePayload(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    reference_url: Optional[str] = None
    expected_price_try: Optional[float] = None


class SuggestionResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    reference_url: Optional[str] = None
    expected_price_try: Optional[float] = None
    status: str
    created_by: UUID
    admin_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SuggestionUpdatePayload(BaseModel):
    status: Optional[SuggestionStatus] = None
    admin_notes: Optional[str] = None


# ── Participant ───────────────────────────────────────────────────────────

class ParticipantResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    user_id: UUID
    quantity: int
    status: str
    campaign_title: str
    campaign_image: Optional[str] = None
    campaign_status: str
    selling_price_try: Optional[float] = None
    total_amount: Optional[float] = None
    moq_fill_percentage: Optional[float] = None
    joined_at: datetime
    invited_at: Optional[datetime] = None
    payment_deadline: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JoinCampaignPayload(BaseModel):
    quantity: int = Field(default=1, ge=1)


# ── Payment V2 ────────────────────────────────────────────────────────────

class PaymentEntryV2Response(BaseModel):
    id: UUID  # participant_id
    campaign_id: UUID
    campaign_title: str
    campaign_image: Optional[str] = None
    quantity: int
    total_amount: float
    status: str
    payment_deadline: Optional[datetime] = None
    stage: str
    lead_time_days: Optional[int] = None

    model_config = {"from_attributes": True}


class PaymentInitiateV2Payload(BaseModel):
    participant_id: UUID


# ── Campaign Progress ─────────────────────────────────────────────────────

class CampaignProgress(BaseModel):
    campaign_id: UUID
    current: int
    target: int
    percentage: float
    selling_price_try: Optional[float] = None
