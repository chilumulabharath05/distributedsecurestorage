"""
Analytics, File Sharing, and Admin API Endpoints
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_optional_user
from app.core.config import settings
from app.core.security import create_share_token, decode_share_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import File as FileModel, SharedLink, UploadLog, User
from app.schemas.schemas import (
    CreateShareLinkRequest,
    DashboardStats,
    MessageResponse,
    ShareLinkResponse,
    UploadLogResponse,
)
from app.services.analytics_service import analytics_service
from app.services.file_service import file_service

logger = logging.getLogger(__name__)

# ─── Analytics Router ─────────────────────────────────────────────────────────
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full dashboard statistics."""
    return await analytics_service.get_dashboard(db, current_user.id)


@analytics_router.get("/activity")
async def get_activity_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    action: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload/download activity logs."""
    query = select(UploadLog).where(UploadLog.user_id == current_user.id)
    if action:
        query = query.where(UploadLog.action == action)
    query = query.order_by(UploadLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "action": log.action,
            "status": log.status,
            "file_id": log.file_id,
            "file_size_bytes": log.file_size_bytes,
            "duration_ms": log.duration_ms,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ─── Sharing Router ───────────────────────────────────────────────────────────
sharing_router = APIRouter(prefix="/share", tags=["File Sharing"])


@sharing_router.post("/", response_model=ShareLinkResponse, status_code=201)
async def create_share_link(
    payload: CreateShareLinkRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a secure, optionally time-limited share link."""
    # Verify file ownership
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == payload.file_id,
            FileModel.owner_id == current_user.id,
            FileModel.status == "ready",
        )
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    token = create_share_token(payload.file_id, current_user.id, payload.expires_hours or 24)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_hours or 24)

    link = SharedLink(
        file_id=payload.file_id,
        created_by=current_user.id,
        token=token,
        token_hash=token_hash,
        permission=payload.permission,
        max_downloads=payload.max_downloads,
        expires_at=expires_at,
        label=payload.label,
        shared_with_email=payload.shared_with_email,
        password_hash=hash_password(payload.password) if payload.password else None,
        is_active=True,
    )
    db.add(link)

    # Log
    log = UploadLog(
        user_id=current_user.id,
        file_id=payload.file_id,
        action="share",
        status="success",
    )
    db.add(log)
    await db.commit()
    await db.refresh(link)

    base_url = str(request.base_url).rstrip("/")
    return ShareLinkResponse(
        id=link.id,
        token=token,
        share_url=f"{base_url}/api/v1/share/access/{token}",
        permission=link.permission,
        expires_at=link.expires_at,
        max_downloads=link.max_downloads,
        download_count=link.download_count,
        is_active=link.is_active,
        label=link.label,
        created_at=link.created_at,
    )


@sharing_router.get("/my-links", response_model=List[ShareLinkResponse])
async def list_my_share_links(
    file_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all share links created by the current user."""
    query = select(SharedLink).where(
        SharedLink.created_by == current_user.id,
        SharedLink.is_revoked == False,
    )
    if file_id:
        query = query.where(SharedLink.file_id == file_id)
    query = query.order_by(SharedLink.created_at.desc())
    result = await db.execute(query)
    links = result.scalars().all()

    return [
        ShareLinkResponse(
            id=lnk.id,
            token=lnk.token,
            share_url=f"/api/v1/share/access/{lnk.token}",
            permission=lnk.permission,
            expires_at=lnk.expires_at,
            max_downloads=lnk.max_downloads,
            download_count=lnk.download_count,
            is_active=lnk.is_active,
            label=lnk.label,
            created_at=lnk.created_at,
        )
        for lnk in links
    ]


@sharing_router.get("/access/{token}")
async def access_shared_file(
    token: str,
    password: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Access a file via share token.
    Returns file metadata or the file itself depending on permission.
    """
    # Decode and validate token
    try:
        claims = decode_share_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Look up link record
    result = await db.execute(
        select(SharedLink).where(
            SharedLink.token == token,
            SharedLink.is_active == True,
            SharedLink.is_revoked == False,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found or revoked")

    # Expiry check
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Share link has expired")

    # Download limit
    if link.max_downloads and link.download_count >= link.max_downloads:
        raise HTTPException(status_code=410, detail="Download limit reached")

    # Password check
    if link.password_hash:
        if not password or not verify_password(password, link.password_hash):
            raise HTTPException(status_code=401, detail="Password required or incorrect")

    # Load file
    file_result = await db.execute(
        select(FileModel).where(FileModel.id == link.file_id, FileModel.status == "ready")
    )
    f = file_result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File no longer available")

    if link.permission == "view":
        return {
            "id": f.id,
            "name": f.original_name,
            "size_bytes": f.size_bytes,
            "mime_type": f.mime_type,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }

    # Download
    data = await file_service.reconstruct_file(db, f.id)
    link.download_count += 1
    link.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()

    import urllib.parse
    from fastapi.responses import Response
    return Response(
        content=data,
        media_type=f.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{urllib.parse.quote(f.original_name)}"',
        },
    )


@sharing_router.delete("/{link_id}", response_model=MessageResponse)
async def revoke_share_link(
    link_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke a share link."""
    result = await db.execute(
        select(SharedLink).where(
            SharedLink.id == link_id,
            SharedLink.created_by == current_user.id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")

    link.is_revoked = True
    link.is_active = False
    await db.commit()
    return MessageResponse(message="Share link revoked")
