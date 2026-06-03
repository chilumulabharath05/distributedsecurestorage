"""
Pydantic Schemas — Request/Response validation
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ─── Common ───────────────────────────────────────────────────────────────────
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


# ─── Auth ─────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username may only contain letters, digits, _ and -")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserPublic"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ─────────────────────────────────────────────────────────────────────
class UserPublic(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    is_verified: bool
    storage_quota_bytes: int
    storage_used_bytes: int
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    bio: Optional[str] = Field(default=None, max_length=500)
    avatar_url: Optional[str] = Field(default=None, max_length=512)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v


# ─── Files ────────────────────────────────────────────────────────────────────
class FileResponse(BaseModel):
    id: str
    owner_id: str
    original_name: str
    mime_type: Optional[str]
    extension: Optional[str]
    size_bytes: int
    sha256_hash: Optional[str]
    status: str
    is_encrypted: bool
    is_duplicate: bool
    storage_savings_bytes: int
    is_public: bool
    download_count: int
    folder_path: str
    tags: Optional[List[str]] = []
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    chunk_count: Optional[int] = 0
    ipfs_folder_cid: Optional[str]

    model_config = {"from_attributes": True}


class FileUpdateRequest(BaseModel):
    original_name: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[List[str]] = None
    folder_path: Optional[str] = None
    is_public: Optional[bool] = None


class FileListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    status: Optional[str] = None
    extension: Optional[str] = None
    folder_path: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


class UploadResponse(BaseModel):
    file_id: str
    original_name: str
    size_bytes: int
    sha256_hash: Optional[str]
    chunk_count: int
    unique_chunks: int
    duplicate_chunks: int
    storage_savings_bytes: int
    dedup_ratio: float
    ipfs_cids: List[str]
    status: str
    message: str


# ─── Chunks ───────────────────────────────────────────────────────────────────
class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    chunk_hash: str
    size_bytes: int
    ipfs_cid: Optional[str]
    is_duplicate: bool
    pinned: bool

    model_config = {"from_attributes": True}


# ─── Sharing ─────────────────────────────────────────────────────────────────
class CreateShareLinkRequest(BaseModel):
    file_id: str
    permission: str = "download"
    expires_hours: Optional[int] = Field(default=24, ge=1, le=720)
    max_downloads: Optional[int] = Field(default=None, ge=1, le=1000)
    password: Optional[str] = None
    label: Optional[str] = Field(default=None, max_length=255)
    shared_with_email: Optional[str] = None


class ShareLinkResponse(BaseModel):
    id: str
    token: str
    share_url: str
    permission: str
    expires_at: Optional[datetime]
    max_downloads: Optional[int]
    download_count: int
    is_active: bool
    label: Optional[str]
    created_at: Optional[datetime]
    file: Optional[FileResponse] = None

    model_config = {"from_attributes": True}


# ─── Analytics ────────────────────────────────────────────────────────────────
class StorageStats(BaseModel):
    total_files: int
    total_size_bytes: int
    storage_used_bytes: int
    storage_quota_bytes: int
    storage_used_percent: float
    total_chunks: int
    unique_chunks: int
    duplicate_chunks: int
    dedup_savings_bytes: int
    dedup_efficiency_percent: float
    ipfs_pinned_chunks: int


class UploadTrendPoint(BaseModel):
    date: str
    upload_count: int
    total_size_bytes: int
    download_count: int


class FileTypeBreakdown(BaseModel):
    extension: str
    count: int
    total_size_bytes: int
    percentage: float


class DashboardStats(BaseModel):
    storage: StorageStats
    recent_uploads: List[FileResponse]
    upload_trend: List[UploadTrendPoint]
    file_types: List[FileTypeBreakdown]
    total_downloads: int
    total_shares: int


# ─── Upload Log ───────────────────────────────────────────────────────────────
class UploadLogResponse(BaseModel):
    id: str
    action: str
    status: str
    file_id: Optional[str]
    file_size_bytes: Optional[int]
    duration_ms: Optional[int]
    ip_address: Optional[str]
    created_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]] = {}

    model_config = {"from_attributes": True}
