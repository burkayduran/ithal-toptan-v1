"""
Create or promote a user to admin.

Usage (from repo root):
    # Create new admin or promote existing user:
    docker compose exec api python scripts/create_admin.py admin@example.com MySecret123

    # Or locally with DATABASE_URL set:
    cd backend && python scripts/create_admin.py admin@example.com MySecret123
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/toplu_alisveris",
)
if "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

from app.models.models import User
from app.core.auth import get_password_hash


async def create_or_promote_admin(email: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.is_admin = True
            user.is_active = True
            # Update password if provided
            user.hashed_password = get_password_hash(password)
            await db.commit()
            print(f"[+] Promoted existing user to admin: {email}")
        else:
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name="Admin",
                is_active=True,
                is_admin=True,
            )
            db.add(user)
            await db.commit()
            print(f"[+] Created admin user: {email}")

    await engine.dispose()


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <email> <password>")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    if len(password) < 8:
        print("Error: password must be at least 8 characters")
        sys.exit(1)

    asyncio.run(create_or_promote_admin(email, password))


if __name__ == "__main__":
    main()
