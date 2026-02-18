"""FastAPI authentication dependencies."""

import logging
from typing import Any

import jwt
from fastapi import Header, HTTPException, status

from ..config import config
from .jwt_auth import decode_token
from .. import database

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: str | None = Header(None),
) -> dict[str, Any] | None:
    """FastAPI dependency: extract and validate user identity from request.

    Returns:
        None          — for mode=none or mode=password (no per-request auth)
        dict          — for mode=jwt or mode=external: {user_id, email, full_name, role?}

    Raises:
        HTTPException 401 — when a token is required but missing/invalid.
    """
    mode = config.auth.mode

    # ── No auth ──
    if mode in ('none', 'password'):
        return None

    # ── JWT / External: require Bearer token ──
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing or invalid Authorization header. Use: Bearer <token>',
        )

    token = authorization.removeprefix('Bearer ').strip()

    try:
        claims = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired',
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Invalid token: {e}',
        )

    if mode == 'jwt':
        # Internal JWT: verify user exists in local DB
        user_id = claims.get('sub')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token missing "sub" claim',
            )
        user = database.get_user_by_id(int(user_id))
        if not user or not user.get('is_active'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='User not found or inactive',
            )
        return {
            'user_id': str(user['id']),
            'email': user['email'],
            'full_name': f"{user['first_name']} {user['last_name']}".strip(),
            'role': user['role'],
        }

    if mode == 'external':
        # External JWT: trust claims directly, no local user lookup
        user_id = claims.get('sub', '')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token missing "sub" claim',
            )
        return {
            'user_id': str(user_id),
            'email': claims.get('email', ''),
            'full_name': claims.get('full_name', ''),
            'role': claims.get('role', ''),
        }

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f'Unknown auth mode: {mode}',
    )
