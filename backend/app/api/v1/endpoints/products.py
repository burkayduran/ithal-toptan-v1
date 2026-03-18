"""
Products endpoints - Public & User Product Requests
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.models.models import ProductRequest, Category, SupplierOffer, WishlistEntry, User
from app.schemas.schemas import (
    ProductRequestCreate,
    ProductResponse,
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

@router.get("", response_model=List[ProductResponse])
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
    query = select(ProductRequest).where(
        ProductRequest.status.in_(["active", "moq_reached", "payment_collecting"])
    )
    
    if category_id:
        query = query.where(ProductRequest.category_id == category_id)
    
    if search:
        query = query.where(
            or_(
                ProductRequest.title.ilike(f"%{search}%"),
                ProductRequest.description.ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(ProductRequest.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Enrich with MoQ data
    enriched_products = []
    for product in products:
        # Get selected offer
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
            "moq_fill_percentage": round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq else None,
        }
        
        enriched_products.append(ProductResponse(**product_dict))
    
    return enriched_products


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
    
    # Increment view count
    product.view_count += 1
    await db.commit()
    
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
        "view_count": product.view_count,
        "created_at": product.created_at,
        "activated_at": product.activated_at,
        "moq": offer.moq if offer else None,
        "selling_price_try": float(offer.selling_price_try) if offer and offer.selling_price_try else None,
        "lead_time_days": offer.lead_time_days if offer else None,
        "current_wishlist_count": wishlist_count,
        "moq_fill_percentage": round(wishlist_count / offer.moq * 100, 1) if offer and offer.moq else None,
    }
    
    return ProductResponse(**product_dict)
