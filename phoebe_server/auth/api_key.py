"""API Key authentication for PHOEBE Server."""

import secrets
import hashlib
import logging
from fastapi import Header, HTTPException, status
from ..config import config

logger = logging.getLogger(__name__)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for storage comparison."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(prefix: str = "phoebe") -> str:
    """
    Generate a secure random API key.

    Args:
        prefix: Prefix to identify the key (default: "phoebe")

    Returns:
        API key in format: prefix_<random_hex>
    """
    random_part = secrets.token_hex(32)  # 64 character hex string
    return f"{prefix}_{random_part}"


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """
    FastAPI dependency to verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The API key if valid

    Raises:
        HTTPException: If auth is enabled and key is invalid/missing
    """
    # If auth is disabled, allow all requests
    if not config.auth.enabled:
        return "auth_disabled"

    # If auth is enabled, require API key
    if not x_api_key:
        logger.warning("Request rejected: Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check if key matches any configured keys
    provided_hash = hash_api_key(x_api_key)

    for valid_key in config.auth.api_keys:
        if provided_hash == hash_api_key(valid_key):
            logger.debug("API key validated successfully")
            return x_api_key

    # Key doesn't match any valid keys
    logger.warning("Request rejected: Invalid API key")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    return config.auth.enabled
