"""
Products endpoints - Public & User Product Requests
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update
from typing import List, Optional
from uuid import UUID

from math import ceil

from app.db.session import get_db
from app.models.models import ProductRequest, Category, SupplierOffer, WishlistEntry, User
from app.schemas.schemas import (
    ProductRequestCreate,
    ProductResponse,
    PaginatedProductResponse,
    CategoryResponse
)
from app.core.auth import get_current_active_user

router = APIRouter()


# ════════════════════════════════════════════════════════════════════════════
# KATEGORİLER (ÖNCE BU - route matching için)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Kategorileri listeler."""
    result = await db.execute(
        select(Category)
        .where(Category.parent_id.is_(None))
        .order_by(Category.sort_order, Category.name)
    )
    categories = result.scalars().all()
    
    return categories


# ════════════════════════════════════════════════════════════════════════════
# KULLANICI ÜRÜN ÖNERİSİ
# ════════════════════════════════════════════════════════════════════════════

@router.post("/request", response_model=dict, status_code=201)
async def create_product_request(
    data: ProductRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kullanıcı ürün önerisi gönderir.
    Status: pending (admin onaylaması gerekir)
    """
    product_request = ProductRequest(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        reference_url=data.reference_url,
        expected_price_try=data.expected_price_try,
        created_by=current_user.id,
        status="pending"  # Admin incelemesi bekliyor
    )
    
    db.add(product_request)
    await db.commit()
    await db.refresh(product_request)
    
    return {
        "id": str(product_request.id),
        "message": "Ürün öneriniz alındı! Admin incelemesi sonrası size bildirim göndereceğiz."
    }


# ════════════════════════════════════════════════════════════════════════════
# AKTİF ÜRÜNLER (Public)
# ════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=PaginatedProductResponse)
async def list_products(
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Aktif ürünleri listeler (admin tarafından yayınlanmış).
    Kullanıcılar sadece bunları görür.
    """
    base_filter = ProductRequest.status.in_(["active", "moq_reached", "payment_collecting"])

    count_query = select(func.count(ProductRequest.id)).where(base_filter)
    query = select(ProductRequest).where(base_filter)

    if category_id:
        count_query = count_query.where(ProductRequest.category_id == category_id)
        query = query.where(ProductRequest.category_id == category_id)

    if search:
        search_filter = or_(
            ProductRequest.title.ilike(f"%{search}%"),
            ProductRequest.description.ilike(f"%{search}%")
        )
        count_query = count_query.where(search_filter)
        query = query.where(search_filter)

    # Total count
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(ProductRequest.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
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

    enriched_products = []
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

        enriched_products.append(ProductResponse(**product_dict))

    return PaginatedProductResponse(
        items=enriched_products,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    """Ürün detayını getirir."""
    result = await db.execute(select(ProductRequest).where(ProductRequest.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Only show active products to public
    if product.status not in ["active", "moq_reached", "payment_collecting", "ordered"]:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Increment view count atomically to avoid race conditions
    await db.execute(
        update(ProductRequest)
        .where(ProductRequest.id == product_id)
        .values(view_count=ProductRequest.view_count + 1)
    )
    await db.commit()
    # Use incremented value for response without a refresh
    current_view_count = product.view_count + 1
    
    # Get offer and wishlist data
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
    
    product_dict = {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "category_id": product.category_id,
        "images": product.images,
        "status": product.status,
        "view_count": current_view_count,
        "created_at": product.created_at,
        "activated_at": product.activated_at,
        "moq": offer.moq if offer else None,
        "selling_price_try": float(offer.selling_price_try) if offer and offer.selling_price_try else None,
        "lead_time_days": offer.lead_time_days if offer else None,
        "current_wishlist_count": wishlist_count,
        "moq_fill_percentage": round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq else None,
    }

    return ProductResponse(**product_dict)


@router.get("/{product_id}/similar", response_model=List[ProductResponse])
async def get_similar_products(
    product_id: UUID,
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Aynı kategorideki benzer aktif ürünleri döndürür."""
    # Get the source product's category
    source = await db.execute(
        select(ProductRequest.category_id).where(ProductRequest.id == product_id)
    )
    category_id = source.scalar_one_or_none()

    # Build filter — same category (if exists), active, exclude self
    query = select(ProductRequest).where(
        ProductRequest.id != product_id,
        ProductRequest.status.in_(["active", "moq_reached", "payment_collecting"]),
    )
    if category_id:
        query = query.where(ProductRequest.category_id == category_id)

    query = query.order_by(ProductRequest.created_at.desc()).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    if not products:
        return []

    product_ids = [p.id for p in products]

    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id.in_(product_ids),
            SupplierOffer.is_selected == True
        )
    )
    offers_map = {o.request_id: o for o in offer_result.scalars().all()}

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

    items = []
    for p in products:
        offer = offers_map.get(p.id)
        wc = counts_map.get(p.id, 0)
        items.append(ProductResponse(
            id=p.id, title=p.title, description=p.description,
            category_id=p.category_id, images=p.images, status=p.status,
            view_count=p.view_count, created_at=p.created_at, activated_at=p.activated_at,
            moq=offer.moq if offer else None,
            selling_price_try=float(offer.selling_price_try) if offer and offer.selling_price_try else None,
            lead_time_days=offer.lead_time_days if offer else None,
            current_wishlist_count=wc,
            moq_fill_percentage=round(wc / offer.moq * 100, 1) if offer and offer.moq else None,
        ))

    return items
