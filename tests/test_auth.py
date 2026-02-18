"""Tests for JWT authentication and password hashing."""

import pytest
from phoebe_server.auth.jwt_auth import create_access_token, decode_token
from phoebe_server.auth.passwords import hash_password, verify_password


def test_password_hash_and_verify():
    """Test password hashing and verification."""
    password = "s3cret!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    """Test JWT access token round-trip."""
    data = {"sub": "user-123", "email": "test@example.com"}
    token = create_access_token(data)
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload


def test_decode_invalid_token():
    """Test decoding an invalid / tampered token raises."""
    with pytest.raises(Exception):
        decode_token("not.a.valid.token")
