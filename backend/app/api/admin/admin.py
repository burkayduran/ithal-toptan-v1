"""
Admin Endpoints - Product & Offer Management
Sadece admin erişebilir
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.models import (
    User, ProductRequest, SupplierOffer, WishlistEntry
)
from app.schemas.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductRequestResponse,
    ProductRequestUpdate,
    SupplierOfferCreate,
    SupplierOfferResponse,
    PriceBreakdown
)
from app.core.auth import require_admin
from app.services.price_service import PriceCalculator

router = APIRouter()


# ════════════════════════════════════════════════════════════════════════════
# ÜRÜN YÖNETİMİ (Admin direkt ürün ekler)
# ════════════════════════════════════════════════════════════════════════════

@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin direkt ürün ekler (Alibaba'dan bulduğu ürün).
    Ürün ve teklif bilgileri aynı anda girilir.
    """
    # 1. Create product
    product = ProductRequest(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        images=data.images,
        status="draft",  # Henüz yayınlanmadı
        created_by=admin.id
    )
    db.add(product)
    await db.flush()  # Get product ID
    
    # 2. Calculate price
    calculator = PriceCalculator()
    price_breakdown = await calculator.calculate_selling_price(
        unit_price_usd=data.unit_price_usd,
        moq=data.moq,
        shipping_cost_usd=data.shipping_cost_usd,
        customs_rate=data.customs_rate,
        margin_rate=data.margin_rate
    )
    
    # 3. Create supplier offer
    offer = SupplierOffer(
        request_id=product.id,
        supplier_name=data.supplier_name,
        supplier_country=data.supplier_country,
        alibaba_product_url=data.alibaba_product_url,
        unit_price_usd=data.unit_price_usd,
        moq=data.moq,
        lead_time_days=data.lead_time_days,
        shipping_cost_usd=data.shipping_cost_usd,
        customs_rate=data.customs_rate,
        usd_rate_used=float(price_breakdown.usd_rate),
        selling_price_try=float(price_breakdown.selling_price_try),
        margin_rate=data.margin_rate,
        is_selected=True  # Otomatik seçili (tek teklif var)
    )
    db.add(offer)
    
    await db.commit()
    await db.refresh(product)
    
    # Enrich response
    product_dict = {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "category_id": product.category_id,
        "images": product.images,
        "status": product.status,
        "view_count": product.view_count,
        "created_at": product.created_at,
        "activated_at": product.activated_at,
        "moq": offer.moq,
        "selling_price_try": float(offer.selling_price_try),
        "lead_time_days": offer.lead_time_days,
        "current_wishlist_count": 0,
        "moq_fill_percentage": 0.0
    }
    
    return ProductResponse(**product_dict)


@router.post("/products/{product_id}/publish")
async def publish_product(
    product_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Ürünü yayınla. Status: draft → active
    Kullanıcılar artık görebilir ve wishlist'e ekleyebilir.
    """
    result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Product is already {product.status}"
        )
    
    # Check if has offer
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == product_id,
            SupplierOffer.is_selected == True
        )
    )
    if not offer_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Product must have an offer before publishing"
        )
    
    # Publish
    product.status = "active"
    product.activated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"message": "Product published successfully", "id": str(product_id)}


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin ürünü günceller."""
    result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if data.title is not None:
        product.title = data.title
    if data.description is not None:
        product.description = data.description
    if data.category_id is not None:
        product.category_id = data.category_id
    if data.images is not None:
        product.images = data.images
    if data.status is not None:
        product.status = data.status
    
    await db.commit()
    await db.refresh(product)
    
    # Get offer
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == product_id,
            SupplierOffer.is_selected == True
        )
    )
    offer = offer_result.scalar_one_or_none()
    
    # Get wishlist count
    count_result = await db.execute(
        select(func.coalesce(func.sum(WishlistEntry.quantity), 0)).where(
            WishlistEntry.request_id == product_id,
            WishlistEntry.status.in_(["waiting", "notified"])
        )
    )
    wishlist_count = count_result.scalar() or 0
    
    product_dict = {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "category_id": product.category_id,
        "images": product.images,
        "status": product.status,
        "view_count": product.view_count,
        "created_at": product.created_at,
        "activated_at": product.activated_at,
        "moq": offer.moq if offer else None,
        "selling_price_try": float(offer.selling_price_try) if offer and offer.selling_price_try else None,
        "lead_time_days": offer.lead_time_days if offer else None,
        "current_wishlist_count": wishlist_count,
        "moq_fill_percentage": round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq > 0 else None,
    }

    return ProductResponse(**product_dict)


@router.get("/products", response_model=List[ProductResponse])
async def list_all_products(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin tüm ürünleri görür (draft dahil)."""
    result = await db.execute(
        select(ProductRequest).order_by(ProductRequest.created_at.desc())
    )
    products = result.scalars().all()
    
    enriched = []
    for product in products:
        # Get offer
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == product.id,
                SupplierOffer.is_selected == True
            )
        )
        offer = offer_result.scalar_one_or_none()
        
        # Get wishlist count
        count_result = await db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0)).where(
                WishlistEntry.request_id == product.id,
                WishlistEntry.status.in_(["waiting", "notified"])
            )
        )
        wishlist_count = count_result.scalar() or 0
        
        product_dict = {
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "category_id": product.category_id,
            "images": product.images,
            "status": product.status,
            "view_count": product.view_count,
            "created_at": product.created_at,
            "activated_at": product.activated_at,
            "moq": offer.moq if offer else None,
            "selling_price_try": float(offer.selling_price_try) if offer and offer.selling_price_try else None,
            "lead_time_days": offer.lead_time_days if offer else None,
            "current_wishlist_count": wishlist_count,
            "moq_fill_percentage": round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq > 0 else None,
        }

        enriched.append(ProductResponse(**product_dict))
    
    return enriched


# ════════════════════════════════════════════════════════════════════════════
# KULLANICI ÖNERİLERİ (User product requests)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/product-requests", response_model=List[ProductRequestResponse])
async def list_product_requests(
    status: str = "pending",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin kullanıcı önerilerini görür."""
    query = select(ProductRequest).where(ProductRequest.status == status)
    query = query.order_by(ProductRequest.created_at.desc())
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    return requests


@router.patch("/product-requests/{request_id}", response_model=ProductRequestResponse)
async def update_product_request(
    request_id: UUID,
    data: ProductRequestUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin kullanıcı önerisini günceller.
    Status: pending → reviewing → approved/rejected
    """
    result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(status_code=404, detail="Product request not found")
    
    if data.status is not None:
        request.status = data.status
    if data.admin_notes is not None:
        request.admin_notes = data.admin_notes
    
    await db.commit()
    await db.refresh(request)
    
    return request


# ════════════════════════════════════════════════════════════════════════════
# FİYAT HESAPLAMA
# ════════════════════════════════════════════════════════════════════════════

@router.post("/calculate-price", response_model=PriceBreakdown)
async def calculate_price_preview(
    data: SupplierOfferCreate,
    admin: User = Depends(require_admin)
):
    """
    Fiyat hesaplama önizlemesi.
    Admin teklif girmeden önce fiyatı görmek için kullanır.
    """
    calculator = PriceCalculator()
    
    price_breakdown = await calculator.calculate_selling_price(
        unit_price_usd=data.unit_price_usd,
        moq=data.moq,
        shipping_cost_usd=data.shipping_cost_usd or 0,
        customs_rate=data.customs_rate or 0.20,
        margin_rate=data.margin_rate
    )
    
    return price_breakdown
