"""
Application Configuration
Environment-driven settings with validation
"""
import secrets
from typing import List, Optional
from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    PROJECT_NAME: str = "CloudStore"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Distributed Secure Cloud Storage with Deduplication"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = secrets.token_urlsafe(64)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    # 32-byte hex string for AES-256
    AES_ENCRYPTION_KEY: str = secrets.token_hex(32)

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/cloudstore"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300          # 5 minutes

    # ── IPFS / Pinata ─────────────────────────────────────────────────────────
    PINATA_JWT: str = ""
    PINATA_API_KEY: str = ""
    PINATA_SECRET_KEY: str = ""
    PINATA_GATEWAY: str = "https://gateway.pinata.cloud/ipfs/"
    IPFS_API_URL: str = "https://api.pinata.cloud"

    # ── File Limits ──────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 500
    CHUNK_SIZE_BYTES: int = 1 * 1024 * 1024    # 1 MB chunks
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "txt", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "jpg", "jpeg", "png", "gif", "webp", "svg", "bmp",
        "mp4", "webm", "mov", "avi", "mkv",
        "mp3", "wav", "ogg", "flac",
        "zip", "tar", "gz", "7z",
        "json", "csv", "xml", "yaml", "yml",
        "py", "js", "ts", "html", "css", "md",
    ]
    BLOCKED_EXTENSIONS: List[str] = [
        "exe", "bat", "cmd", "sh", "ps1", "msi", "dll", "so",
        "php", "asp", "aspx", "jsp", "cgi",
        "vbs", "wsf", "scr", "pif", "com",
    ]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    UPLOAD_RATE_LIMIT: str = "20/minute"
    AUTH_RATE_LIMIT: str = "5/minute"

    # ── CORS ─────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://cloudstore.vercel.app",
    ]

    # ── Storage ──────────────────────────────────────────────────────────────
    DEFAULT_STORAGE_QUOTA_GB: float = 5.0     # 5 GB free tier
    TEMP_UPLOAD_DIR: str = "/tmp/cloudstore_uploads"

    # ── Email (optional) ─────────────────────────────────────────────────────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
