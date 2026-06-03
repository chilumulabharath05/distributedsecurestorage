"""
Unit Tests — Security, Chunking, Hashing
"""
import pytest
from app.core.security import (
    FileEncryption,
    compute_merkle_root,
    get_file_extension,
    hash_password,
    is_extension_allowed,
    sanitize_filename,
    sha256_bytes,
    verify_password,
)
from app.core.config import settings


# ── Password ──────────────────────────────────────────────────────────────────
def test_password_hash_verify():
    pwd = "TestPass123!"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(pwd, h)
    assert not verify_password("Wrong1!", h)


def test_password_hash_unique():
    h1 = hash_password("Same1!")
    h2 = hash_password("Same1!")
    assert h1 != h2  # bcrypt salts


# ── AES Encryption ────────────────────────────────────────────────────────────
def test_aes_encrypt_decrypt_roundtrip():
    enc = FileEncryption(key_hex="0" * 64)
    data = b"Hello CloudStore! " * 500
    ct, nonce = enc.encrypt_chunk(data)
    assert ct != data
    assert enc.decrypt_chunk(ct, nonce) == data


def test_aes_unique_nonces():
    enc = FileEncryption(key_hex="0" * 64)
    data = b"same data"
    _, n1 = enc.encrypt_chunk(data)
    _, n2 = enc.encrypt_chunk(data)
    assert n1 != n2


def test_aes_b64_roundtrip():
    enc = FileEncryption(key_hex="a" * 64)
    data = b"base64 roundtrip test"
    ct_b64, nonce_b64 = enc.encrypt_to_b64(data)
    assert enc.decrypt_from_b64(ct_b64, nonce_b64) == data


def test_aes_wrong_key_fails():
    enc1 = FileEncryption(key_hex="0" * 64)
    enc2 = FileEncryption(key_hex="1" * 64)
    ct, nonce = enc1.encrypt_chunk(b"secret")
    with pytest.raises(Exception):
        enc2.decrypt_chunk(ct, nonce)


# ── SHA-256 ───────────────────────────────────────────────────────────────────
def test_sha256_deterministic():
    d = b"cloudstore test data"
    assert sha256_bytes(d) == sha256_bytes(d)
    assert len(sha256_bytes(d)) == 64


def test_sha256_unique():
    assert sha256_bytes(b"a") != sha256_bytes(b"b")


# ── Merkle Root ───────────────────────────────────────────────────────────────
def test_merkle_single():
    h = sha256_bytes(b"only")
    assert compute_merkle_root([h]) == h


def test_merkle_multiple():
    hashes = [sha256_bytes(f"chunk-{i}".encode()) for i in range(4)]
    root = compute_merkle_root(hashes)
    assert len(root) == 64
    assert compute_merkle_root(hashes) == root          # deterministic
    assert compute_merkle_root(hashes[::-1]) != root   # order-sensitive


def test_merkle_empty():
    assert compute_merkle_root([]) == ""


def test_merkle_odd_chunks():
    hashes = [sha256_bytes(f"c{i}".encode()) for i in range(3)]
    root = compute_merkle_root(hashes)
    assert len(root) == 64


# ── File Validation ───────────────────────────────────────────────────────────
def test_extension_allowed():
    assert is_extension_allowed("document.pdf")
    assert is_extension_allowed("image.jpg")
    assert is_extension_allowed("data.csv")


def test_extension_blocked():
    assert not is_extension_allowed("virus.exe")
    assert not is_extension_allowed("shell.sh")
    assert not is_extension_allowed("script.php")


def test_get_extension():
    assert get_file_extension("file.PDF") == "pdf"
    assert get_file_extension("no_extension") == ""
    assert get_file_extension("file.tar.gz") == "gz"


def test_sanitize_filename():
    assert sanitize_filename("normal_file.txt") == "normal_file.txt"
    assert sanitize_filename("../etc/passwd") != "../etc/passwd"
    assert sanitize_filename("  .hidden  ") != ""


# ── JWT ───────────────────────────────────────────────────────────────────────
def test_jwt_create_decode():
    from app.core.security import create_access_token, decode_token
    token = create_access_token("user-123", {"role": "user"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "user"
    assert payload["type"] == "access"


def test_jwt_invalid_raises():
    from app.core.security import decode_token
    with pytest.raises(ValueError):
        decode_token("not.a.valid.jwt")


def test_jwt_expired_raises():
    from app.core.security import decode_token
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    payload = {
        "sub": "x", "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        "type": "access", "jti": "test"
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(ValueError, match="expired"):
        decode_token(token)


# ── Chunking ─────────────────────────────────────────────────────────────────
def test_fixed_chunking_reassembly():
    from app.services.file_service import FileService
    data = b"X" * (3 * 1024 * 1024 + 512)
    chunks = FileService._fixed_chunk(data, 1024 * 1024)
    assert len(chunks) == 4
    assert b"".join(chunks) == data


def test_chunking_small_file():
    from app.services.file_service import FileService
    data = b"tiny"
    chunks = FileService._fixed_chunk(data, 1024 * 1024)
    assert len(chunks) == 1
    assert chunks[0] == data
