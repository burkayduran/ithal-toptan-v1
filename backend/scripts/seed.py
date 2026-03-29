"""
Idempotent seed script — safe to run multiple times.
Creates demo categories, products, and campaigns for local development.

Usage (from repo root):
    docker compose exec api python scripts/seed.py
    # or locally with DATABASE_URL set:
    cd backend && python scripts/seed.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Allow running from repo root or backend/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/toplu_alisveris",
)
if "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Import models after path is set
from app.models.models import Category, Product, Campaign  # noqa: E402


CATEGORIES = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Elektronik",
        "slug": "elektronik",
        "icon": "laptop",
        "sort_order": 1,
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "name": "Ev & Yaşam",
        "slug": "ev-yasam",
        "icon": "home",
        "sort_order": 2,
    },
]

PRODUCTS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0001-000000000001"),
        "title": "USB-C Hub 7-in-1",
        "description": (
            "Dizüstü bilgisayarınız için 7 portlu USB-C hub. "
            "HDMI 4K, 3x USB-A 3.0, SD kart okuyucu, USB-C PD 100W şarj desteği."
        ),
        "category_slug": "elektronik",
        "images": [
            "https://images.unsplash.com/photo-1625842268584-8f3296236761?w=800&q=80"
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0001-000000000002"),
        "title": "Bambu Masa Organizeri Seti",
        "description": (
            "5 parçalı bambu masa organizeri seti. "
            "Kalemlik, telefon standı, küçük çekmece ve 2 açık göz içerir."
        ),
        "category_slug": "ev-yasam",
        "images": [
            "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=800&q=80"
        ],
    },
]

CAMPAIGNS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0002-000000000001"),
        "product_id": uuid.UUID("00000000-0000-0000-0001-000000000001"),
        "status": "active",
        "moq": 50,
        "selling_price_try_snapshot": 1299.0,
        "unit_price_usd_snapshot": 18.50,
        "shipping_cost_usd_snapshot": 95.0,
        "margin_rate_snapshot": 0.25,
        "fx_rate_snapshot": 38.0,
        "lead_time_days": 21,
        "activated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        # Seeded with some mock participants via moq_fill to look real
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0002-000000000002"),
        "product_id": uuid.UUID("00000000-0000-0000-0001-000000000002"),
        "status": "moq_reached",
        "moq": 30,
        "selling_price_try_snapshot": 499.0,
        "unit_price_usd_snapshot": 6.50,
        "shipping_cost_usd_snapshot": 60.0,
        "margin_rate_snapshot": 0.20,
        "fx_rate_snapshot": 38.0,
        "lead_time_days": 14,
        "activated_at": datetime(2026, 2, 15, tzinfo=timezone.utc),
        "moq_reached_at": datetime(2026, 3, 10, tzinfo=timezone.utc),
    },
]


async def seed(db: AsyncSession) -> None:
    # ── Categories ──────────────────────────────────────────────────────────
    cat_map: dict[str, uuid.UUID] = {}
    for cat_data in CATEGORIES:
        existing = await db.get(Category, cat_data["id"])
        if not existing:
            cat = Category(
                id=cat_data["id"],
                name=cat_data["name"],
                slug=cat_data["slug"],
                icon=cat_data.get("icon"),
                sort_order=cat_data.get("sort_order", 0),
            )
            db.add(cat)
            print(f"  [+] Category: {cat_data['name']}")
        else:
            print(f"  [=] Category already exists: {cat_data['name']}")
        cat_map[cat_data["slug"]] = cat_data["id"]

    await db.flush()

    # ── Products ─────────────────────────────────────────────────────────────
    for prod_data in PRODUCTS:
        existing = await db.get(Product, prod_data["id"])
        if not existing:
            product = Product(
                id=prod_data["id"],
                title=prod_data["title"],
                description=prod_data["description"],
                category_id=cat_map[prod_data["category_slug"]],
                images=prod_data.get("images", []),
            )
            db.add(product)
            print(f"  [+] Product: {prod_data['title']}")
        else:
            print(f"  [=] Product already exists: {prod_data['title']}")

    await db.flush()

    # ── Campaigns ─────────────────────────────────────────────────────────────
    for camp_data in CAMPAIGNS:
        existing = await db.get(Campaign, camp_data["id"])
        if not existing:
            campaign = Campaign(
                id=camp_data["id"],
                product_id=camp_data["product_id"],
                status=camp_data["status"],
                moq=camp_data["moq"],
                selling_price_try_snapshot=camp_data.get("selling_price_try_snapshot"),
                unit_price_usd_snapshot=camp_data.get("unit_price_usd_snapshot"),
                shipping_cost_usd_snapshot=camp_data.get("shipping_cost_usd_snapshot"),
                margin_rate_snapshot=camp_data.get("margin_rate_snapshot"),
                fx_rate_snapshot=camp_data.get("fx_rate_snapshot"),
                lead_time_days=camp_data.get("lead_time_days"),
                activated_at=camp_data.get("activated_at"),
                moq_reached_at=camp_data.get("moq_reached_at"),
            )
            db.add(campaign)

            # Fetch product title for display
            prod = await db.get(Product, camp_data["product_id"])
            print(f"  [+] Campaign: {prod.title if prod else camp_data['product_id']} ({camp_data['status']})")
        else:
            print(f"  [=] Campaign already exists: {camp_data['id']}")

    await db.commit()


async def main() -> None:
    print("Seeding demo data...")
    async with AsyncSessionLocal() as db:
        await seed(db)
    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
