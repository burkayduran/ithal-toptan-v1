from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.core.config import settings
from app.db.session import get_db
from app.core.redis import get_redis
from app.core.limiter import limiter
from app.models.models import User
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token, UserUpdate
from app.core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_and_rotate_refresh_token,
    revoke_refresh_token,
    get_current_active_user,
)

router = APIRouter()

_REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Write the refresh token as an httpOnly, SameSite=lax cookie."""
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        # secure=True in production (HTTPS only); False when DEBUG so tests pass over HTTP
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(
    request: Request,
    user_data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Register a new user. Returns access token; sets refresh token cookie."""
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, redis)
    _set_refresh_cookie(response, refresh_token)

    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Login. Returns access token; sets refresh token cookie."""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id, redis)
    _set_refresh_cookie(response, refresh_token)

    return Token(access_token=access_token)


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    response: Response,
    redis: aioredis.Redis = Depends(get_redis),
):
    """Exchange a valid refresh token (httpOnly cookie) for a new access token.

    The refresh token is rotated on every use: the old JTI is deleted from Redis
    and a fresh one is issued, so a stolen token can only be replayed once before
    detection on the next legitimate use.
    """
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing",
        )

    new_refresh, user_id = await verify_and_rotate_refresh_token(token, redis)
    _set_refresh_cookie(response, new_refresh)

    return Token(access_token=create_access_token(data={"sub": str(user_id)}))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    redis: aioredis.Redis = Depends(get_redis),
):
    """Revoke the refresh token and clear the cookie."""
    token = request.cookies.get(_REFRESH_COOKIE)
    if token:
        await revoke_refresh_token(token, redis)
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/v1/auth")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user information."""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.city is not None:
        current_user.city = user_update.city
    if user_update.district is not None:
        current_user.district = user_update.district
    if user_update.address is not None:
        current_user.address = user_update.address

    await db.commit()
    await db.refresh(current_user)

    return current_user
