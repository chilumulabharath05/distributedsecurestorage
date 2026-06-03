"""
Security Module
- JWT token creation/verification
- Password hashing (bcrypt)
- AES-256-GCM file encryption
- SHA-256 chunk hashing
"""
import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ─── Password ────────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against bcrypt hash."""
    return pwd_context.verify(plain, hashed)


# ─── JWT ─────────────────────────────────────────────────────────────────────
def create_access_token(subject: str, extra: Dict[str, Any] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT. Raises ValueError on failure."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def create_share_token(file_id: str, user_id: str, expires_hours: int = 24) -> str:
    """Create a signed share token for file sharing."""
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {
        "file_id": file_id,
        "user_id": user_id,
        "exp": expire,
        "type": "share",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_share_token(token: str) -> Dict[str, Any]:
    """Decode a share token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "share":
            raise ValueError("Not a share token")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid share token: {e}")


# ─── AES-256-GCM Encryption ──────────────────────────────────────────────────
class FileEncryption:
    """
    AES-256-GCM symmetric encryption for file chunks.
    Each chunk gets a unique 96-bit nonce.
    """

    def __init__(self, key_hex: Optional[str] = None):
        raw_key = bytes.fromhex(key_hex or settings.AES_ENCRYPTION_KEY)
        if len(raw_key) != 32:
            raise ValueError("AES key must be exactly 32 bytes (256 bits)")
        self.aesgcm = AESGCM(raw_key)

    def encrypt_chunk(self, data: bytes) -> Tuple[bytes, bytes]:
        """
        Encrypt a chunk.
        Returns (ciphertext_with_tag, nonce).
        """
        nonce = os.urandom(12)   # 96-bit nonce recommended for GCM
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        return ciphertext, nonce

    def decrypt_chunk(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """Decrypt a chunk."""
        return self.aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_to_b64(self, data: bytes) -> Tuple[str, str]:
        """Encrypt and return base64-encoded (ciphertext, nonce)."""
        ct, nonce = self.encrypt_chunk(data)
        return base64.b64encode(ct).decode(), base64.b64encode(nonce).decode()

    def decrypt_from_b64(self, ct_b64: str, nonce_b64: str) -> bytes:
        """Decrypt from base64-encoded inputs."""
        ct = base64.b64decode(ct_b64)
        nonce = base64.b64decode(nonce_b64)
        return self.decrypt_chunk(ct, nonce)

    @staticmethod
    def generate_key() -> str:
        """Generate a new random 32-byte key as hex string."""
        return os.urandom(32).hex()


# ─── Hashing ─────────────────────────────────────────────────────────────────
def sha256_bytes(data: bytes) -> str:
    """SHA-256 hash of bytes → hex string."""
    return hashlib.sha256(data).hexdigest()


def sha256_file_stream(file_path: str, chunk_size: int = 8192) -> str:
    """Streaming SHA-256 of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(chunk_size), b""):
            h.update(block)
    return h.hexdigest()


def compute_merkle_root(hashes: list[str]) -> str:
    """
    Compute Merkle root from list of hex-encoded SHA-256 hashes.
    Used to verify complete file integrity.
    """
    if not hashes:
        return ""
    if len(hashes) == 1:
        return hashes[0]
    nodes = [bytes.fromhex(h) for h in hashes]
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [
            hashlib.sha256(nodes[i] + nodes[i + 1]).digest()
            for i in range(0, len(nodes), 2)
        ]
    return nodes[0].hex()


# ─── File Validation ─────────────────────────────────────────────────────────
def get_file_extension(filename: str) -> str:
    """Extract lowercase extension from filename."""
    parts = filename.rsplit(".", 1)
    return parts[-1].lower() if len(parts) > 1 else ""


def is_extension_allowed(filename: str) -> bool:
    ext = get_file_extension(filename)
    if ext in settings.BLOCKED_EXTENSIONS:
        return False
    return ext in settings.ALLOWED_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename."""
    import re
    # Keep only safe characters
    safe = re.sub(r"[^\w\s\-.]", "", filename)
    safe = safe.strip(". ")
    return safe or "unnamed_file"


# Singleton
file_encryptor = FileEncryption()
