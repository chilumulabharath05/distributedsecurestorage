"""
Authentication API Endpoints
Register, Login, Logout, Refresh, Profile
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, rate_limit
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
    UserUpdate,
)
from app.services.auth_service import auth_service
from app.core.security import hash_password, verify_password
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_to_schema(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_verified=user.is_verified,
        storage_quota_bytes=user.storage_quota_bytes,
        storage_used_bytes=user.storage_used_bytes,
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    await rate_limit(request, limit=5, window=60)
    try:
        user, access, refresh = await auth_service.register(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=60 * 24 * 60,  # minutes → seconds
        user=_user_to_schema(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    await rate_limit(request, limit=10, window=60)
    try:
        user, access, refresh = await auth_service.login(db, payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=60 * 24 * 60,
        user=_user_to_schema(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rotate access + refresh tokens."""
    try:
        new_access, new_refresh = await auth_service.refresh_tokens(db, payload.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=60 * 24 * 60,
        user=_user_to_schema(current_user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invalidate refresh token."""
    await auth_service.logout(db, current_user.id)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return _user_to_schema(current_user)


@router.patch("/me", response_model=UserPublic)
async def update_profile(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user profile."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    await db.commit()
    await db.refresh(current_user)
    return _user_to_schema(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change user password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.refresh_token_hash = None  # invalidate all sessions
    await db.commit()
    return MessageResponse(message="Password changed successfully. Please log in again.")
