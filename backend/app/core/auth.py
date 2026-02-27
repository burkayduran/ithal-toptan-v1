import uuid as _uuid_module
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.core.config import settings
from app.db.session import get_db
from app.models.models import User

# Password hashing with Argon2 (modern, secure, no bcrypt limits)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer security
security = HTTPBearer()

# JWT signing algorithm (sourced from settings so .env ALGORITHM=HS256 is consistent)
ALGORITHM = settings.ALGORITHM

_REFRESH_PREFIX = "rt:"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(user_id: UUID, redis: aioredis.Redis) -> str:
    """Create a long-lived refresh token and store its JTI in Redis.

    The token is a signed JWT containing the JTI (unique ID) so the
    server-side Redis entry can be deleted on logout, providing true
    revocation without a DB lookup on every access-token request.
    """
    jti = str(_uuid_module.uuid4())
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.set(f"{_REFRESH_PREFIX}{jti}", str(user_id), ex=ttl_seconds)
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": jti,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


async def verify_and_rotate_refresh_token(
    token: str, redis: aioredis.Redis
) -> tuple[str, UUID]:
    """Validate a refresh token and rotate it atomically.

    Returns the *new* refresh-token string and the user's UUID.
    Raises HTTP 401 on any validation failure (expired, revoked, wrong type).
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise invalid

    if payload.get("type") != "refresh":
        raise invalid

    jti: str = payload.get("jti", "")
    user_id_str: str = payload.get("sub", "")
    if not jti or not user_id_str:
        raise invalid

    stored = await redis.get(f"{_REFRESH_PREFIX}{jti}")
    if stored is None or stored != user_id_str:
        raise invalid  # revoked or already rotated

    # Delete current JTI first (rotation – prevents replay)
    await redis.delete(f"{_REFRESH_PREFIX}{jti}")
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise invalid

    new_token = await create_refresh_token(user_id, redis)
    return new_token, user_id


async def revoke_refresh_token(token: str, redis: aioredis.Redis) -> None:
    """Delete the refresh token's JTI from Redis (logout / password change)."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti", "")
        if jti:
            await redis.delete(f"{_REFRESH_PREFIX}{jti}")
    except JWTError:
        pass  # token already invalid – nothing to revoke


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        
        # Convert string to UUID (CRITICAL FIX)
        try:
            user_id = UUID(user_id_str)
        except (ValueError, AttributeError):
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user. is_active is already enforced by get_current_user."""
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user
