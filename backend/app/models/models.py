"""
SQLAlchemy ORM Models
Tables: users, files, chunks, upload_logs, shared_links
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ─── Users ───────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    bio = Column(Text, nullable=True)

    # Role & Status
    role = Column(
        Enum("user", "admin", name="user_role"),
        default="user", nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Storage
    storage_quota_bytes = Column(
        BigInteger,
        default=5 * 1024 * 1024 * 1024,   # 5 GB
        nullable=False,
    )
    storage_used_bytes = Column(BigInteger, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Refresh token tracking
    refresh_token_hash = Column(String(256), nullable=True)

    # Relationships
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    upload_logs = relationship("UploadLog", back_populates="user", cascade="all, delete-orphan")
    shared_links = relationship("SharedLink", back_populates="created_by_user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
    )

    def __repr__(self):
        return f"<User {self.email}>"


# ─── Files ───────────────────────────────────────────────────────────────────
class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    owner_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File info
    original_name = Column(String(512), nullable=False)
    stored_name = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=True)
    extension = Column(String(32), nullable=True)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)

    # Integrity
    sha256_hash = Column(String(64), nullable=True, index=True)   # whole-file hash
    merkle_root = Column(String(64), nullable=True)                # Merkle root of chunks

    # Status
    status = Column(
        Enum("uploading", "processing", "ready", "error", "deleted", name="file_status"),
        default="uploading",
        nullable=False,
    )
    upload_progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)

    # Encryption
    is_encrypted = Column(Boolean, default=True, nullable=False)
    encryption_version = Column(String(16), default="aes-256-gcm")

    # Deduplication
    is_duplicate = Column(Boolean, default=False)
    storage_savings_bytes = Column(BigInteger, default=0)

    # IPFS
    ipfs_folder_cid = Column(String(128), nullable=True)

    # Sharing
    is_public = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    # Folder (simple path-based organization)
    folder_path = Column(String(1024), default="/", nullable=False)

    # Relationships
    owner = relationship("User", back_populates="files")
    chunks = relationship("Chunk", back_populates="file", cascade="all, delete-orphan")
    upload_logs = relationship("UploadLog", back_populates="file")
    shared_links = relationship("SharedLink", back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_files_owner_status", "owner_id", "status"),
        Index("idx_files_sha256", "sha256_hash"),
        Index("idx_files_owner_folder", "owner_id", "folder_path"),
    )


# ─── Chunks ──────────────────────────────────────────────────────────────────
class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    file_id = Column(
        UUID(as_uuid=False),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk identity
    chunk_index = Column(Integer, nullable=False)
    chunk_hash = Column(String(64), nullable=False, index=True)    # SHA-256 of plaintext
    size_bytes = Column(BigInteger, nullable=False)
    encrypted_size_bytes = Column(BigInteger, nullable=True)

    # Encryption metadata (stored per chunk)
    nonce_b64 = Column(String(64), nullable=True)   # base64-encoded 12-byte nonce

    # IPFS
    ipfs_cid = Column(String(128), nullable=True, index=True)
    pinned = Column(Boolean, default=False)
    pin_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Deduplication
    is_duplicate = Column(Boolean, default=False)
    original_chunk_id = Column(
        UUID(as_uuid=False),
        ForeignKey("chunks.id"),
        nullable=True,
    )
    reference_count = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file = relationship("File", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("file_id", "chunk_index", name="uq_chunk_file_index"),
        Index("idx_chunks_hash", "chunk_hash", "is_duplicate"),
        Index("idx_chunks_cid", "ipfs_cid"),
    )


# ─── Upload Logs ─────────────────────────────────────────────────────────────
class UploadLog(Base):
    __tablename__ = "upload_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id = Column(
        UUID(as_uuid=False),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Activity
    action = Column(
        Enum("upload", "download", "delete", "share", "preview", "rename",
            name="log_action"),
        nullable=False,
    )
    status = Column(
        Enum("success", "failure", "in_progress", name="log_status"),
        default="success",
    )
    error_message = Column(Text, nullable=True)

    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_ms = Column(Integer, nullable=True)   # processing time
    log_metadata = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="upload_logs")
    file = relationship("File", back_populates="upload_logs")

    __table_args__ = (
        Index("idx_logs_user_action", "user_id", "action"),
        Index("idx_logs_created", "created_at"),
    )


# ─── Shared Links ────────────────────────────────────────────────────────────
class SharedLink(Base):
    __tablename__ = "shared_links"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    file_id = Column(
        UUID(as_uuid=False),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Token
    token = Column(String(256), unique=True, nullable=False, index=True)
    token_hash = Column(String(64), nullable=False)   # SHA-256 of token

    # Permissions
    permission = Column(
        Enum("view", "download", name="share_permission"),
        default="download",
    )
    password_hash = Column(String(255), nullable=True)  # optional password protection
    max_downloads = Column(Integer, nullable=True)      # None = unlimited
    download_count = Column(Integer, default=0)

    # Validity
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)

    # Metadata
    label = Column(String(255), nullable=True)
    shared_with_email = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    file = relationship("File", back_populates="shared_links")
    created_by_user = relationship("User", back_populates="shared_links")

    __table_args__ = (
        Index("idx_shared_token", "token"),
        Index("idx_shared_file", "file_id", "is_active"),
    )
