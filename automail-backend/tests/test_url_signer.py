import uuid

import pytest

from app.utils.url_signer import sign_open_token, verify_open_token

SECRET = "test-secret-key"


def test_roundtrip():
    lead_id = uuid.uuid4()
    email_id = uuid.uuid4()
    token = sign_open_token(lead_id, email_id, SECRET)
    got_lead, got_email = verify_open_token(token, SECRET)
    assert got_lead == lead_id
    assert got_email == email_id


def test_tampered_token_raises():
    lead_id = uuid.uuid4()
    email_id = uuid.uuid4()
    token = sign_open_token(lead_id, email_id, SECRET)
    # flip one character in the middle
    chars = list(token)
    chars[len(chars) // 2] = "X" if chars[len(chars) // 2] != "X" else "Y"
    tampered = "".join(chars)
    with pytest.raises(ValueError, match="invalid"):
        verify_open_token(tampered, SECRET)


def test_wrong_secret_raises():
    lead_id = uuid.uuid4()
    email_id = uuid.uuid4()
    token = sign_open_token(lead_id, email_id, SECRET)
    with pytest.raises(ValueError):
        verify_open_token(token, "wrong-secret")


def test_bad_base64_raises():
    with pytest.raises(ValueError):
        verify_open_token("not-valid-base64!!!", SECRET)
