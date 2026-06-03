"""
Analytics Service — Dashboard stats, trends, file type breakdown
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Chunk, File, SharedLink, UploadLog, User

logger = logging.getLogger(__name__)


class AnalyticsService:

    async def get_dashboard(self, db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Compile full dashboard data for a user."""
        storage = await self._get_storage_stats(db, user_id)
        recent = await self._get_recent_uploads(db, user_id, limit=8)
        trend = await self._get_upload_trend(db, user_id, days=30)
        file_types = await self._get_file_types(db, user_id)
        totals = await self._get_totals(db, user_id)

        return {
            "storage": storage,
            "recent_uploads": recent,
            "upload_trend": trend,
            "file_types": file_types,
            **totals,
        }

    async def _get_storage_stats(self, db: AsyncSession, user_id: str) -> Dict:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        stats = await db.execute(
            select(
                func.count(File.id).label("total_files"),
                func.coalesce(func.sum(File.size_bytes), 0).label("total_size"),
                func.coalesce(func.sum(File.storage_savings_bytes), 0).label("total_savings"),
            ).where(File.owner_id == user_id, File.status == "ready")
        )
        row = stats.one()

        chunk_stats = await db.execute(
            select(
                func.count(Chunk.id).label("total"),
                func.count(Chunk.id).filter(Chunk.is_duplicate == False).label("unique"),
                func.count(Chunk.id).filter(Chunk.pinned == True).label("pinned"),
            ).join(File).where(File.owner_id == user_id, File.status == "ready")
        )
        cr = chunk_stats.one()

        total_size = int(row.total_size)
        savings = int(row.total_savings)
        used = user.storage_used_bytes if user else 0
        quota = user.storage_quota_bytes if user else 1
        dup_chunks = int(cr.total or 0) - int(cr.unique or 0)
        dedup_pct = (savings / (total_size + savings) * 100) if (total_size + savings) > 0 else 0

        return {
            "total_files": int(row.total_files or 0),
            "total_size_bytes": total_size,
            "storage_used_bytes": used,
            "storage_quota_bytes": quota,
            "storage_used_percent": round((used / quota * 100) if quota else 0, 2),
            "total_chunks": int(cr.total or 0),
            "unique_chunks": int(cr.unique or 0),
            "duplicate_chunks": dup_chunks,
            "dedup_savings_bytes": savings,
            "dedup_efficiency_percent": round(dedup_pct, 2),
            "ipfs_pinned_chunks": int(cr.pinned or 0),
        }

    async def _get_recent_uploads(
        self, db: AsyncSession, user_id: str, limit: int = 8
    ) -> List[Dict]:
        result = await db.execute(
            select(File)
            .where(File.owner_id == user_id, File.status == "ready")
            .order_by(File.created_at.desc())
            .limit(limit)
        )
        files = result.scalars().all()
        return [self._file_to_dict(f) for f in files]

async def _get_upload_trend(
    self, db: AsyncSession, user_id: str, days: int = 30
) -> List[Dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    day_bucket = func.date_trunc(
        "day",
        UploadLog.created_at
    ).label("day")

    result = await db.execute(
        select(
            day_bucket,
            func.count(UploadLog.id)
                .filter(UploadLog.action == "upload")
                .label("uploads"),
            func.count(UploadLog.id)
                .filter(UploadLog.action == "download")
                .label("downloads"),
            func.coalesce(
                func.sum(UploadLog.file_size_bytes)
                    .filter(UploadLog.action == "upload"),
                0
            ).label("size"),
        )
        .where(
            UploadLog.user_id == user_id,
            UploadLog.created_at >= since
        )
        .group_by(day_bucket)
        .order_by(day_bucket)
    )

    rows = result.all()

    return [
        {
            "date": row.day.strftime("%Y-%m-%d") if row.day else "",
            "upload_count": int(row.uploads or 0),
            "total_size_bytes": int(row.size or 0),
            "download_count": int(row.downloads or 0),
        }
        for row in rows
    ]

    async def _get_file_types(self, db: AsyncSession, user_id: str) -> List[Dict]:
        result = await db.execute(
            select(
                File.extension,
                func.count(File.id).label("count"),
                func.coalesce(func.sum(File.size_bytes), 0).label("total_size"),
            )
            .where(File.owner_id == user_id, File.status == "ready")
            .group_by(File.extension)
            .order_by(func.count(File.id).desc())
            .limit(10)
        )
        rows = result.all()
        total_count = sum(r.count for r in rows) or 1
        return [
            {
                "extension": r.extension or "unknown",
                "count": int(r.count),
                "total_size_bytes": int(r.total_size),
                "percentage": round(r.count / total_count * 100, 1),
            }
            for r in rows
        ]

    async def _get_totals(self, db: AsyncSession, user_id: str) -> Dict:
        dl_result = await db.execute(
            select(func.count(UploadLog.id)).where(
                UploadLog.user_id == user_id,
                UploadLog.action == "download",
            )
        )
        share_result = await db.execute(
            select(func.count(SharedLink.id)).where(
                SharedLink.created_by == user_id
            )
        )
        return {
            "total_downloads": int(dl_result.scalar() or 0),
            "total_shares": int(share_result.scalar() or 0),
        }

    @staticmethod
    def _file_to_dict(f: File) -> Dict:
        return {
            "id": f.id,
            "original_name": f.original_name,
            "size_bytes": f.size_bytes,
            "mime_type": f.mime_type,
            "extension": f.extension,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }


analytics_service = AnalyticsService()
