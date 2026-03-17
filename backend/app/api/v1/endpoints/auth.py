from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token, UserUpdate
from app.core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user
)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user."""
    # Find user by email
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
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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
