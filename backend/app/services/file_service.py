"""
File Service
Upload pipeline: validate → hash → chunk → deduplicate → encrypt → IPFS → DB
"""
import io
import logging
import os
import time
import zlib
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    compute_merkle_root,
    file_encryptor,
    get_file_extension,
    is_extension_allowed,
    sanitize_filename,
    sha256_bytes,
)
from app.models.models import Chunk, File, UploadLog
from app.services.ipfs_service import ipfs_service

logger = logging.getLogger(__name__)


class FileService:
    """
    Orchestrates the full file lifecycle.
    """

    # ── Upload Pipeline ───────────────────────────────────────────────────────
    async def process_upload(
        self,
        db: AsyncSession,
        user_id: str,
        raw_data: bytes,
        filename: str,
        mime_type: str,
        folder_path: str = "/",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Full upload pipeline:
        1. Validate & sanitize
        2. Compute whole-file hash
        3. Compress + chunk
        4. Deduplicate chunks
        5. Encrypt unique chunks
        6. Upload unique chunks to IPFS
        7. Persist to DB
        """
        start_ts = time.monotonic()
        _prog = lambda p, msg: progress_cb(p, msg) if progress_cb else None

        # ── 1. Validate ───────────────────────────────────────────────────────
        if len(raw_data) == 0:
            raise ValueError("Empty file")
        if len(raw_data) > settings.max_file_size_bytes:
            raise ValueError(f"File exceeds {settings.MAX_FILE_SIZE_MB} MB limit")
        safe_name = sanitize_filename(filename)
        if not is_extension_allowed(safe_name):
            ext = get_file_extension(safe_name)
            raise ValueError(f"File type '.{ext}' is not allowed")
        _prog(5, "Validating file...")

        # ── 2. Whole-file hash ────────────────────────────────────────────────
        file_hash = sha256_bytes(raw_data)
        _prog(10, "Computing hash...")

        # ── 3. Chunk the data ─────────────────────────────────────────────────
        chunks = self._fixed_chunk(raw_data, settings.CHUNK_SIZE_BYTES)
        chunk_hashes = [sha256_bytes(c) for c in chunks]
        merkle_root = compute_merkle_root(chunk_hashes)
        _prog(20, f"Split into {len(chunks)} chunks...")

        # ── 4. Deduplicate ────────────────────────────────────────────────────
        dedup_result = await self._deduplicate(db, chunks, chunk_hashes)
        unique_chunks   = dedup_result["unique"]      # [(idx, data, hash)]
        dup_chunks      = dedup_result["duplicates"]  # [(idx, hash, existing_cid)]
        savings_bytes   = sum(len(chunks[i]) for i, _, _ in dup_chunks)
        _prog(35, f"{len(dup_chunks)} duplicate chunks found...")

        # ── 5. Encrypt unique chunks ──────────────────────────────────────────
        encrypted_payloads: List[Tuple[int, bytes, bytes, str]] = []  # (idx, ct, nonce, hash)
        for idx, data, chunk_hash in unique_chunks:
            ct, nonce = file_encryptor.encrypt_chunk(data)
            encrypted_payloads.append((idx, ct, nonce, chunk_hash))
        _prog(50, "Encrypting chunks...")

        # ── 6. Upload to IPFS ────────────────────────────────────────────────
        upload_batch = [
            (ct, f"{file_hash[:16]}_chunk_{idx:04d}.enc")
            for idx, ct, nonce, h in encrypted_payloads
        ]
        ipfs_responses = []
        if upload_batch:
            ipfs_responses = await ipfs_service.pin_chunks_batch(
                upload_batch, max_concurrent=5, file_id=""
            )
        _prog(80, "Uploading to IPFS...")

        # Build CID map for unique chunks
        unique_cid_map: Dict[int, str] = {}  # chunk_index → cid
        nonce_map: Dict[int, bytes] = {}
        for (idx, ct, nonce, h), resp in zip(encrypted_payloads, ipfs_responses):
            unique_cid_map[idx] = resp["IpfsHash"] if resp else None
            nonce_map[idx] = nonce

        # ── 7. DB Records ────────────────────────────────────────────────────
        ext = get_file_extension(safe_name)
        file_record = File(
            owner_id=user_id,
            original_name=safe_name,
            stored_name=f"{file_hash[:16]}_{safe_name}",
            mime_type=mime_type,
            extension=ext,
            size_bytes=len(raw_data),
            sha256_hash=file_hash,
            merkle_root=merkle_root,
            is_encrypted=True,
            status="ready",
            upload_progress=100.0,
            storage_savings_bytes=savings_bytes,
            is_duplicate=False,
            folder_path=folder_path,
            description=description,
            tags=tags or [],
        )
        db.add(file_record)
        await db.flush()  # get file_record.id

        # Store all chunks (unique + duplicate references)
        all_cids: List[str] = []
        for idx, chunk_data in enumerate(chunks):
            h = chunk_hashes[idx]
            is_dup = any(di == idx for di, _, _ in dup_chunks)
            dup_cid = None
            if is_dup:
                dup_match = next((c for di, _, c in dup_chunks if di == idx), None)
                dup_cid = dup_match

            cid = dup_cid if is_dup else unique_cid_map.get(idx)
            nonce = nonce_map.get(idx)

            import base64
            chunk_record = Chunk(
                file_id=file_record.id,
                chunk_index=idx,
                chunk_hash=h,
                size_bytes=len(chunk_data),
                encrypted_size_bytes=len(unique_cid_map.get(idx, "") or ""),
                nonce_b64=base64.b64encode(nonce).decode() if nonce else None,
                ipfs_cid=cid,
                pinned=cid is not None,
                pin_timestamp=datetime.now(timezone.utc) if cid else None,
                is_duplicate=is_dup,
            )
            db.add(chunk_record)
            if cid:
                all_cids.append(cid)

        # Upload log
        duration_ms = int((time.monotonic() - start_ts) * 1000)
        log = UploadLog(
            user_id=user_id,
            file_id=file_record.id,
            action="upload",
            status="success",
            file_size_bytes=len(raw_data),
            duration_ms=duration_ms,
        )
        db.add(log)
        await db.commit()
        await db.refresh(file_record)

        _prog(100, "Upload complete!")
        dedup_ratio = savings_bytes / len(raw_data) if raw_data else 0

        return {
            "file_id": file_record.id,
            "original_name": safe_name,
            "size_bytes": len(raw_data),
            "sha256_hash": file_hash,
            "chunk_count": len(chunks),
            "unique_chunks": len(unique_chunks),
            "duplicate_chunks": len(dup_chunks),
            "storage_savings_bytes": savings_bytes,
            "dedup_ratio": round(dedup_ratio, 4),
            "ipfs_cids": list(set(all_cids)),
            "status": "ready",
            "message": f"Uploaded successfully. Saved {savings_bytes} bytes via deduplication.",
        }

    # ── Download ──────────────────────────────────────────────────────────────
    async def reconstruct_file(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: Optional[str] = None,
    ) -> bytes:
        """
        Retrieve all chunks from IPFS, decrypt, and reassemble the original file.
        """
        # Load file record
        result = await db.execute(
            select(File).where(
                File.id == file_id,
                File.status == "ready",
            )
        )
        file_rec = result.scalar_one_or_none()
        if not file_rec:
            raise FileNotFoundError(f"File {file_id} not found")
        if user_id and file_rec.owner_id != user_id and not file_rec.is_public:
            raise PermissionError("Access denied")

        # Load chunks
        chunks_result = await db.execute(
            select(Chunk)
            .where(Chunk.file_id == file_id)
            .order_by(Chunk.chunk_index)
        )
        chunks = chunks_result.scalars().all()
        if not chunks:
            raise ValueError("No chunks found for file")

        # Collect unique CIDs
        cids = list(set(c.ipfs_cid for c in chunks if c.ipfs_cid))
        cid_data = await ipfs_service.retrieve_chunks_batch(cids)

        # Reassemble and decrypt
        import base64
        reassembled = b""
        for chunk in sorted(chunks, key=lambda c: c.chunk_index):
            raw = cid_data.get(chunk.ipfs_cid)
            if raw is None:
                raise ValueError(f"Missing chunk {chunk.chunk_index} (CID: {chunk.ipfs_cid})")
            if chunk.nonce_b64 and file_rec.is_encrypted:
                nonce = base64.b64decode(chunk.nonce_b64)
                plain = file_encryptor.decrypt_chunk(raw, nonce)
            else:
                plain = raw
            reassembled += plain

        # Verify integrity
        actual_hash = sha256_bytes(reassembled)
        if file_rec.sha256_hash and actual_hash != file_rec.sha256_hash:
            logger.error(f"Integrity mismatch for file {file_id}")
            raise ValueError("File integrity check failed")

        return reassembled

    # ── Delete ────────────────────────────────────────────────────────────────
    async def delete_file(self, db: AsyncSession, file_id: str, user_id: str) -> bool:
        """Soft-delete a file."""
        result = await db.execute(
            select(File).where(File.id == file_id, File.owner_id == user_id)
        )
        file_rec = result.scalar_one_or_none()
        if not file_rec:
            return False
        file_rec.status = "deleted"
        file_rec.deleted_at = datetime.now(timezone.utc)

        log = UploadLog(
            user_id=user_id,
            file_id=file_id,
            action="delete",
            status="success",
        )
        db.add(log)
        await db.commit()
        return True

    # ── Stats ─────────────────────────────────────────────────────────────────
    async def get_user_stats(self, db: AsyncSession, user_id: str) -> Dict[str, Any]:
        from app.models.models import User
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return {}

        # File stats
        file_stats = await db.execute(
            select(
                func.count(File.id).label("total_files"),
                func.sum(File.size_bytes).label("total_size"),
                func.sum(File.storage_savings_bytes).label("total_savings"),
            ).where(File.owner_id == user_id, File.status == "ready")
        )
        fs = file_stats.one()

        # Chunk stats
        chunk_stats = await db.execute(
            select(
                func.count(Chunk.id).label("total_chunks"),
                func.count(Chunk.id).filter(Chunk.is_duplicate == False).label("unique_chunks"),
                func.count(Chunk.id).filter(Chunk.is_duplicate == True).label("dup_chunks"),
                func.count(Chunk.id).filter(Chunk.pinned == True).label("pinned"),
            ).join(File).where(File.owner_id == user_id, File.status == "ready")
        )
        cs = chunk_stats.one()

        total_size = int(fs.total_size or 0)
        total_savings = int(fs.total_savings or 0)
        used = user.storage_used_bytes
        quota = user.storage_quota_bytes
        dedup_pct = (total_savings / (total_size + total_savings) * 100) if (total_size + total_savings) > 0 else 0

        return {
            "total_files": int(fs.total_files or 0),
            "total_size_bytes": total_size,
            "storage_used_bytes": used,
            "storage_quota_bytes": quota,
            "storage_used_percent": round((used / quota * 100) if quota else 0, 2),
            "total_chunks": int(cs.total_chunks or 0),
            "unique_chunks": int(cs.unique_chunks or 0),
            "duplicate_chunks": int(cs.dup_chunks or 0),
            "dedup_savings_bytes": total_savings,
            "dedup_efficiency_percent": round(dedup_pct, 2),
            "ipfs_pinned_chunks": int(cs.pinned or 0),
        }

    # ── Internals ─────────────────────────────────────────────────────────────
    @staticmethod
    def _fixed_chunk(data: bytes, chunk_size: int) -> List[bytes]:
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    @staticmethod
    async def _deduplicate(
        db: AsyncSession,
        chunks: List[bytes],
        hashes: List[str],
    ) -> Dict[str, List]:
        """
        Check each chunk hash against existing chunks.
        Returns {unique: [(idx, data, hash)], duplicates: [(idx, hash, existing_cid)]}.
        """
        from sqlalchemy import and_
        existing = await db.execute(
            select(Chunk.chunk_hash, Chunk.ipfs_cid)
            .where(
                Chunk.chunk_hash.in_(hashes),
                Chunk.is_duplicate == False,
                Chunk.ipfs_cid.isnot(None),
            )
            .group_by(Chunk.chunk_hash, Chunk.ipfs_cid)
        )
        existing_map = {row.chunk_hash: row.ipfs_cid for row in existing}

        unique, duplicates = [], []
        for idx, (chunk, h) in enumerate(zip(chunks, hashes)):
            if h in existing_map:
                duplicates.append((idx, h, existing_map[h]))
            else:
                unique.append((idx, chunk, h))
        return {"unique": unique, "duplicates": duplicates}


file_service = FileService()
