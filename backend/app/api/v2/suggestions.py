"""
V2 Suggestion endpoints — user product suggestions.
Primary source: product_suggestions table.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.session import get_db
from app.models.models import ProductSuggestion, User
from app.schemas.v2_schemas import SuggestionCreatePayload

router = APIRouter()


@router.post("", status_code=201)
async def create_suggestion(
    data: SuggestionCreatePayload,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a product suggestion."""
    suggestion = ProductSuggestion(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        reference_url=data.reference_url,
        expected_price_try=data.expected_price_try,
        status="pending",
        created_by=current_user.id,
    )
    db.add(suggestion)

    await db.commit()
    await db.refresh(suggestion)

    return {
        "id": str(suggestion.id),
        "message": "Ürün öneriniz alındı! Admin incelemesi sonrası size bildirim göndereceğiz.",
    }
