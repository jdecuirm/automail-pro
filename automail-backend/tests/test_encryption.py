"""Tests for Fernet encryption helpers."""

from __future__ import annotations

import pytest


def test_encryption_roundtrip():
    from app.services.encryption import decrypt_str, encrypt_str

    plaintext = "user@example.com"
    ciphertext = encrypt_str(plaintext)
    assert isinstance(ciphertext, bytes)
    assert decrypt_str(ciphertext) == plaintext


def test_encryption_different_ciphertexts_same_plaintext():
    """Fernet uses a random IV so the same plaintext produces different ciphertexts."""
    from app.services.encryption import encrypt_str

    ct1 = encrypt_str("identical")
    ct2 = encrypt_str("identical")
    assert ct1 != ct2


def test_encryption_wrong_key_raises():
    from app.services.encryption import decrypt_str
    from cryptography.fernet import Fernet, InvalidToken

    other_key = Fernet.generate_key()
    wrong_fernet = Fernet(other_key)
    ciphertext = wrong_fernet.encrypt(b"secret")
    with pytest.raises(InvalidToken):
        decrypt_str(ciphertext)


def test_fernet_key_missing_fails(monkeypatch):
    """Settings must raise ValidationError if FERNET_KEY is not set."""
    monkeypatch.delenv("FERNET_KEY", raising=False)
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
