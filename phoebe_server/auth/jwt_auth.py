"""JWT token creation and validation."""

import time
import logging
import jwt
from ..config import config

logger = logging.getLogger(__name__)


def create_access_token(data: dict) -> str:
    """Create a JWT access token.

    Args:
        data: Claims to include (sub, email, full_name, role, etc.)

    Returns:
        Encoded JWT string.
    """
    payload = {**data}
    expire = time.time() + (config.auth.jwt_expire_minutes * 60)
    payload["exp"] = expire

    if config.auth.jwt_issuer:
        payload["iss"] = config.auth.jwt_issuer

    return jwt.encode(payload, config.auth.jwt_secret_key, algorithm=config.auth.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded claims dict.

    Raises:
        jwt.InvalidTokenError: If token is invalid or expired.
    """
    kwargs: dict = {
        "algorithms": [config.auth.jwt_algorithm],
    }
    if config.auth.jwt_issuer:
        kwargs["issuer"] = config.auth.jwt_issuer

    return jwt.decode(token, config.auth.jwt_secret_key, **kwargs)
