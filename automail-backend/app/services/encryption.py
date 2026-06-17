"""Fernet symmetric encryption helpers for sensitive fields."""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    """Return cached Fernet instance using settings.fernet_key."""
    key = get_settings().fernet_key.get_secret_value()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_str(plaintext: str) -> bytes:
    """Encrypt a string. Returns Fernet token bytes."""
    return get_fernet().encrypt(plaintext.encode())


def decrypt_str(ciphertext: bytes) -> str:
    """Decrypt a Fernet token. Raises cryptography.fernet.InvalidToken on failure."""
    return get_fernet().decrypt(ciphertext).decode()
