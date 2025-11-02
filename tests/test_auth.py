"""Tests for API key authentication."""

import pytest
from fastapi import HTTPException
from phoebe_server.auth.api_key import generate_api_key, hash_api_key, verify_api_key
from phoebe_server.config import config


def test_generate_api_key():
    """Test API key generation."""
    key = generate_api_key()
    assert key.startswith("phoebe_")
    assert len(key) > 20

    # Test custom prefix
    key = generate_api_key(prefix="test")
    assert key.startswith("test_")


def test_hash_api_key():
    """Test API key hashing."""
    key = "test_key_123"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)

    # Same key should produce same hash
    assert hash1 == hash2

    # Different keys should produce different hashes
    hash3 = hash_api_key("different_key")
    assert hash1 != hash3


@pytest.mark.asyncio
async def test_verify_api_key_disabled():
    """Test that verification passes when auth is disabled."""
    # Save original state
    original_enabled = config.auth.enabled

    try:
        config.auth.enabled = False
        result = await verify_api_key(None)
        assert result == "auth_disabled"
    finally:
        config.auth.enabled = original_enabled


@pytest.mark.asyncio
async def test_verify_api_key_missing():
    """Test that missing key raises 401 when auth is enabled."""
    # Save original state
    original_enabled = config.auth.enabled

    try:
        config.auth.enabled = True
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(None)
        assert exc_info.value.status_code == 401
    finally:
        config.auth.enabled = original_enabled


@pytest.mark.asyncio
async def test_verify_api_key_invalid():
    """Test that invalid key raises 403."""
    # Save original state
    original_enabled = config.auth.enabled
    original_keys = config.auth.api_keys

    try:
        config.auth.enabled = True
        config.auth.api_keys = ["valid_key_123"]

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key("wrong_key")
        assert exc_info.value.status_code == 403
    finally:
        config.auth.enabled = original_enabled
        config.auth.api_keys = original_keys


@pytest.mark.asyncio
async def test_verify_api_key_valid():
    """Test that valid key is accepted."""
    # Save original state
    original_enabled = config.auth.enabled
    original_keys = config.auth.api_keys

    try:
        valid_key = "test_key_456"
        config.auth.enabled = True
        config.auth.api_keys = [valid_key]

        result = await verify_api_key(valid_key)
        assert result == valid_key
    finally:
        config.auth.enabled = original_enabled
        config.auth.api_keys = original_keys
