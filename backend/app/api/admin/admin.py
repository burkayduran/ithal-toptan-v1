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

from sqlalchemy.exc import IntegrityError as SQLIntegrityError

from app.db.session import get_db
from app.models.models import (
    User, ProductRequest, SupplierOffer, WishlistEntry, Category
)
from app.schemas.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    AdminProductDetailResponse,
    ProductRequestResponse,
    ProductRequestUpdate,
    SupplierOfferCreate,
    SupplierOfferResponse,
    PriceBreakdown,
    PriceCalculateRequest,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
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


@router.patch("/products/{product_id}", response_model=AdminProductDetailResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin ürünü günceller — tedarikçi/fiyat değişirse yeniden fiyatlandırır."""
    result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # A1: Ödeme süreci başlamış kampanyalarda fiyat/tedarikçi değişikliğini engelle
    LOCKED_STATUSES = {"moq_reached", "payment_collecting", "ordered"}
    LOCKED_FIELDS = [
        "unit_price_usd", "moq", "shipping_cost_usd", "customs_rate",
        "margin_rate", "supplier_name", "supplier_country", "alibaba_product_url",
    ]
    if product.status in LOCKED_STATUSES:
        for field_name in LOCKED_FIELDS:
            if getattr(data, field_name, None) is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Ödeme süreci başlamış kampanyalarda fiyat ve tedarikçi bilgileri değiştirilemez.",
                )

    # Update product fields
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

    # Update supplier / offer fields if provided
    pricing_changed = any(
        v is not None for v in [
            data.unit_price_usd, data.moq, data.shipping_cost_usd,
            data.customs_rate, data.margin_rate,
        ]
    )

    if offer and (pricing_changed or any(
        v is not None for v in [
            data.supplier_name, data.supplier_country,
            data.alibaba_product_url, data.lead_time_days,
        ]
    )):
        if data.supplier_name is not None:
            offer.supplier_name = data.supplier_name
        if data.supplier_country is not None:
            offer.supplier_country = data.supplier_country
        if data.alibaba_product_url is not None:
            offer.alibaba_product_url = data.alibaba_product_url
        if data.lead_time_days is not None:
            offer.lead_time_days = data.lead_time_days
        if data.unit_price_usd is not None:
            offer.unit_price_usd = data.unit_price_usd
        if data.moq is not None:
            offer.moq = data.moq
        if data.shipping_cost_usd is not None:
            offer.shipping_cost_usd = data.shipping_cost_usd
        if data.customs_rate is not None:
            offer.customs_rate = data.customs_rate
        if data.margin_rate is not None:
            offer.margin_rate = data.margin_rate

        # Recalculate selling price if any pricing input changed
        if pricing_changed:
            calculator = PriceCalculator()
            price_breakdown = await calculator.calculate_selling_price(
                unit_price_usd=float(offer.unit_price_usd),
                moq=int(offer.moq),
                shipping_cost_usd=float(offer.shipping_cost_usd or 0),
                customs_rate=float(offer.customs_rate or 0.35),
                margin_rate=float(offer.margin_rate or 0.30),
            )
            offer.selling_price_try = float(price_breakdown.selling_price_try)
            offer.usd_rate_used = float(price_breakdown.usd_rate)

        await db.commit()
        await db.refresh(offer)

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
        "moq_fill_percentage": round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq else None,
        # Supplier / offer detail
        "supplier_name": offer.supplier_name if offer else None,
        "supplier_country": offer.supplier_country if offer else None,
        "alibaba_product_url": offer.alibaba_product_url if offer else None,
        "unit_price_usd": float(offer.unit_price_usd) if offer and offer.unit_price_usd else None,
        "shipping_cost_usd": float(offer.shipping_cost_usd) if offer and offer.shipping_cost_usd else None,
        "customs_rate": float(offer.customs_rate) if offer and offer.customs_rate else None,
        "margin_rate": float(offer.margin_rate) if offer and offer.margin_rate else None,
    }

    return AdminProductDetailResponse(**product_dict)


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

    if not products:
        return []

    product_ids = [p.id for p in products]

    # Batch: offers
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id.in_(product_ids),
            SupplierOffer.is_selected == True
        )
    )
    offers_map = {o.request_id: o for o in offer_result.scalars().all()}

    # Batch: wishlist counts
    count_result = await db.execute(
        select(
            WishlistEntry.request_id,
            func.coalesce(func.sum(WishlistEntry.quantity), 0)
        )
        .where(
            WishlistEntry.request_id.in_(product_ids),
            WishlistEntry.status.in_(["waiting", "notified"])
        )
        .group_by(WishlistEntry.request_id)
    )
    counts_map = {row[0]: int(row[1]) for row in count_result.all()}

    enriched = []
    for product in products:
        offer = offers_map.get(product.id)
        wishlist_count = counts_map.get(product.id, 0)

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
            "moq_fill_percentage": round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq else None,
        }

        enriched.append(ProductResponse(**product_dict))

    return enriched


@router.get("/products/{product_id}", response_model=AdminProductDetailResponse)
async def get_product(
    product_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin tek ürünü getirir (draft dahil) — tedarikçi/fiyat alanları dahil."""
    result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == product_id,
            SupplierOffer.is_selected == True
        )
    )
    offer = offer_result.scalar_one_or_none()

    count_result = await db.execute(
        select(func.coalesce(func.sum(WishlistEntry.quantity), 0)).where(
            WishlistEntry.request_id == product_id,
            WishlistEntry.status.in_(["waiting", "notified"])
        )
    )
    wishlist_count = count_result.scalar() or 0

    return AdminProductDetailResponse(
        id=product.id,
        title=product.title,
        description=product.description,
        category_id=product.category_id,
        images=product.images,
        status=product.status,
        view_count=product.view_count,
        created_at=product.created_at,
        activated_at=product.activated_at,
        moq=offer.moq if offer else None,
        selling_price_try=float(offer.selling_price_try) if offer and offer.selling_price_try else None,
        lead_time_days=offer.lead_time_days if offer else None,
        current_wishlist_count=wishlist_count,
        moq_fill_percentage=round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq else None,
        # Supplier / offer detail fields
        supplier_name=offer.supplier_name if offer else None,
        supplier_country=offer.supplier_country if offer else None,
        alibaba_product_url=offer.alibaba_product_url if offer else None,
        unit_price_usd=float(offer.unit_price_usd) if offer and offer.unit_price_usd else None,
        shipping_cost_usd=float(offer.shipping_cost_usd) if offer and offer.shipping_cost_usd else None,
        customs_rate=float(offer.customs_rate) if offer and offer.customs_rate else None,
        margin_rate=float(offer.margin_rate) if offer and offer.margin_rate else None,
    )


@router.post("/products/bulk-publish")
async def bulk_publish(
    product_ids: List[UUID],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Birden fazla taslak ürünü toplu yayınlar."""
    published = []
    failed = []

    for pid in product_ids:
        result = await db.execute(
            select(ProductRequest).where(ProductRequest.id == pid)
        )
        product = result.scalar_one_or_none()

        if not product:
            failed.append({"id": str(pid), "reason": "Ürün bulunamadı"})
            continue

        if product.status != "draft":
            failed.append({"id": str(pid), "reason": f"Durum zaten '{product.status}'"})
            continue

        # Check offer exists
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == pid,
                SupplierOffer.is_selected == True,
            )
        )
        if not offer_result.scalar_one_or_none():
            failed.append({"id": str(pid), "reason": "Teklif bulunamadı"})
            continue

        product.status = "active"
        product.activated_at = datetime.now(timezone.utc)
        published.append(str(pid))

    await db.commit()

    return {"published": published, "failed": failed}


@router.post("/products/bulk-cancel")
async def bulk_cancel(
    product_ids: List[UUID],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Birden fazla ürünü toplu iptal eder."""
    cancelled = []
    failed = []

    for pid in product_ids:
        result = await db.execute(
            select(ProductRequest).where(ProductRequest.id == pid)
        )
        product = result.scalar_one_or_none()

        if not product:
            failed.append({"id": str(pid), "reason": "Ürün bulunamadı"})
            continue

        if product.status in ["ordered", "delivered"]:
            failed.append({"id": str(pid), "reason": f"'{product.status}' durumundaki ürün iptal edilemez"})
            continue

        product.status = "cancelled"
        cancelled.append(str(pid))

    await db.commit()

    return {"cancelled": cancelled, "failed": failed}


# ════════════════════════════════════════════════════════════════════════════
# KATEGORİ YÖNETİMİ
# ════════════════════════════════════════════════════════════════════════════

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Tüm kategorileri listeler."""
    result = await db.execute(
        select(Category).order_by(Category.sort_order, Category.name)
    )
    return result.scalars().all()


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Yeni kategori ekler."""
    category = Category(
        name=data.name,
        slug=data.slug,
        parent_id=data.parent_id,
        gumruk_rate=data.gumruk_rate,
        is_restricted=data.is_restricted,
        icon=data.icon,
        sort_order=data.sort_order,
    )
    db.add(category)
    try:
        await db.commit()
    except SQLIntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu slug zaten kullanılıyor.")
    await db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Kategoriyi günceller."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.name is not None:
        category.name = data.name
    if data.slug is not None:
        category.slug = data.slug
    if data.parent_id is not None:
        category.parent_id = data.parent_id
    if data.gumruk_rate is not None:
        category.gumruk_rate = data.gumruk_rate
    if data.is_restricted is not None:
        category.is_restricted = data.is_restricted
    if data.icon is not None:
        category.icon = data.icon
    if data.sort_order is not None:
        category.sort_order = data.sort_order

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Kategoriyi siler. Ürün atanmışsa hata döner."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        await db.delete(category)
        await db.commit()
    except SQLIntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Bu kategoriye atanmış ürünler var. Önce ürünleri taşıyın."
        )


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
    data: PriceCalculateRequest,
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
        shipping_cost_usd=data.shipping_cost_usd,
        customs_rate=data.customs_rate,
        margin_rate=data.margin_rate
    )

    return price_breakdown
