"""
Files API Endpoints
Upload, download, list, delete, preview, metadata
"""
import logging
import urllib.parse
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Query, Request, UploadFile, status,
)
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, rate_limit
from app.db.session import get_db
from app.models.models import Chunk, File as FileModel, UploadLog
from app.schemas.schemas import (
    FileResponse, FileUpdateRequest, MessageResponse, UploadResponse
)
from app.services.file_service import file_service
from app.models.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["Files"])


def _file_schema(f: FileModel, chunk_count: int = 0) -> FileResponse:
    return FileResponse(
        id=f.id,
        owner_id=f.owner_id,
        original_name=f.original_name,
        mime_type=f.mime_type,
        extension=f.extension,
        size_bytes=f.size_bytes,
        sha256_hash=f.sha256_hash,
        status=f.status,
        is_encrypted=f.is_encrypted,
        is_duplicate=f.is_duplicate,
        storage_savings_bytes=f.storage_savings_bytes,
        is_public=f.is_public,
        download_count=f.download_count,
        folder_path=f.folder_path,
        tags=f.tags or [],
        description=f.description,
        created_at=f.created_at,
        updated_at=f.updated_at,
        last_accessed_at=f.last_accessed_at,
        chunk_count=chunk_count,
        ipfs_folder_cid=f.ipfs_folder_cid,
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder_path: str = Form(default="/"),
    description: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file — it is validated, encrypted, chunked,
    deduplicated, and stored on IPFS.
    """
    await rate_limit(request, limit=20, window=60)

    raw = await file.read()
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        result = await file_service.process_upload(
            db=db,
            user_id=current_user.id,
            raw_data=raw,
            filename=file.filename or "upload",
            mime_type=file.content_type or "application/octet-stream",
            folder_path=folder_path,
            description=description,
            tags=tag_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")

    # Update user storage quota
    current_user.storage_used_bytes += result["size_bytes"] - result["storage_savings_bytes"]
    await db.commit()

    return UploadResponse(**result)


@router.get("/", response_model=List[FileResponse])
async def list_files(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    extension: Optional[str] = Query(default=None),
    folder_path: Optional[str] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's files with search and pagination."""
    query = select(FileModel).where(
        FileModel.owner_id == current_user.id,
        FileModel.status == "ready",
    )
    if search:
        query = query.where(
            or_(
                FileModel.original_name.ilike(f"%{search}%"),
                FileModel.description.ilike(f"%{search}%"),
            )
        )
    if extension:
        query = query.where(FileModel.extension == extension.lower())
    if folder_path:
        query = query.where(FileModel.folder_path == folder_path)

    sort_col = getattr(FileModel, sort_by, FileModel.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    files = result.scalars().all()

    out = []
    for f in files:
        count_res = await db.execute(
            select(func.count(Chunk.id)).where(Chunk.file_id == f.id)
        )
        out.append(_file_schema(f, count_res.scalar() or 0))
    return out


@router.get("/stats")
async def get_file_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get storage statistics for the current user."""
    return await file_service.get_user_stats(db, current_user.id)


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get file metadata by ID."""
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.owner_id == current_user.id,
            FileModel.status != "deleted",
        )
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    count_res = await db.execute(
        select(func.count(Chunk.id)).where(Chunk.file_id == file_id)
    )
    return _file_schema(f, count_res.scalar() or 0)


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download and reconstruct an encrypted file."""
    # Verify ownership
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.owner_id == current_user.id,
            FileModel.status == "ready",
        )
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        data = await file_service.reconstruct_file(db, file_id, current_user.id)
    except (FileNotFoundError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Update stats
    f.download_count += 1
    from datetime import datetime, timezone
    f.last_accessed_at = datetime.now(timezone.utc)
    log = UploadLog(
        user_id=current_user.id,
        file_id=file_id,
        action="download",
        status="success",
        file_size_bytes=f.size_bytes,
    )
    db.add(log)
    await db.commit()

    safe_name = urllib.parse.quote(f.original_name)
    return Response(
        content=data,
        media_type=f.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Length": str(len(data)),
            "X-File-Hash": f.sha256_hash or "",
        },
    )


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return file for inline preview (images, PDFs, text)."""
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.owner_id == current_user.id,
            FileModel.status == "ready",
        )
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    previewable = ["image/", "application/pdf", "text/"]
    if not any((f.mime_type or "").startswith(p) for p in previewable):
        raise HTTPException(status_code=415, detail="File type not previewable")

    try:
        data = await file_service.reconstruct_file(db, file_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=data,
        media_type=f.mime_type or "application/octet-stream",
        headers={"Content-Disposition": "inline"},
    )


@router.patch("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: str,
    payload: FileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update file metadata."""
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.owner_id == current_user.id,
        )
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    if payload.original_name is not None:
        from app.core.security import sanitize_filename
        f.original_name = sanitize_filename(payload.original_name)
    if payload.description is not None:
        f.description = payload.description
    if payload.tags is not None:
        f.tags = payload.tags
    if payload.folder_path is not None:
        f.folder_path = payload.folder_path
    if payload.is_public is not None:
        f.is_public = payload.is_public

    await db.commit()
    await db.refresh(f)
    return _file_schema(f)


@router.delete("/{file_id}", response_model=MessageResponse)
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a file."""
    deleted = await file_service.delete_file(db, file_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    # Reclaim storage
    result = await db.execute(select(FileModel).where(FileModel.id == file_id))
    f = result.scalar_one_or_none()
    if f:
        reclaim = f.size_bytes - f.storage_savings_bytes
        current_user.storage_used_bytes = max(0, current_user.storage_used_bytes - reclaim)
        await db.commit()

    return MessageResponse(message="File deleted successfully")


@router.get("/{file_id}/chunks")
async def get_file_chunks(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chunk details for a file."""
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.owner_id == current_user.id,
        )
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    chunks_result = await db.execute(
        select(Chunk)
        .where(Chunk.file_id == file_id)
        .order_by(Chunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()
    return [
        {
            "id": c.id,
            "index": c.chunk_index,
            "hash": c.chunk_hash,
            "size_bytes": c.size_bytes,
            "ipfs_cid": c.ipfs_cid,
            "is_duplicate": c.is_duplicate,
            "pinned": c.pinned,
        }
        for c in chunks
    ]
