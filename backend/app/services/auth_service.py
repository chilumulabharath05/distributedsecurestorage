"""
Authentication Service
User registration, login, token management, profile
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.models import User
from app.schemas.schemas import RegisterRequest, UserPublic

logger = logging.getLogger(__name__)


class AuthService:

    async def register(
        self,
        db: AsyncSession,
        data: RegisterRequest,
    ) -> Tuple[User, str, str]:
        """Register new user. Returns (user, access_token, refresh_token)."""
        # Uniqueness checks
        existing_email = await db.execute(
            select(User).where(User.email == data.email)
        )
        if existing_email.scalar_one_or_none():
            raise ValueError("Email already registered")

        existing_user = await db.execute(
            select(User).where(User.username == data.username.lower())
        )
        if existing_user.scalar_one_or_none():
            raise ValueError("Username already taken")

        user = User(
            email=data.email,
            username=data.username.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role="user",
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        access = create_access_token(user.id, {"role": user.role})
        refresh = create_refresh_token(user.id)

        # Store refresh token hash
        user.refresh_token_hash = hashlib.sha256(refresh.encode()).hexdigest()
        await db.commit()

        logger.info(f"User registered: {user.email}")
        return user, access, refresh

    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Tuple[User, str, str]:
        """Login. Returns (user, access_token, refresh_token)."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account disabled")
        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        user.last_login_at = datetime.now(timezone.utc)
        access = create_access_token(user.id, {"role": user.role})
        refresh = create_refresh_token(user.id)
        user.refresh_token_hash = hashlib.sha256(refresh.encode()).hexdigest()
        await db.commit()

        return user, access, refresh

    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> Tuple[str, str]:
        """Rotate refresh token. Returns (new_access, new_refresh)."""
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("Not a refresh token")
        except ValueError as e:
            raise ValueError(f"Token invalid: {e}")

        # Verify stored hash
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await db.execute(
            select(User).where(User.id == payload["sub"])
        )
        user = result.scalar_one_or_none()
        if not user or user.refresh_token_hash != token_hash:
            raise ValueError("Refresh token revoked or invalid")

        # Rotate
        new_access = create_access_token(user.id, {"role": user.role})
        new_refresh = create_refresh_token(user.id)
        user.refresh_token_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
        await db.commit()
        return new_access, new_refresh

    async def get_user_by_id(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def logout(self, db: AsyncSession, user_id: str) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.refresh_token_hash = None
            await db.commit()


auth_service = AuthService()
