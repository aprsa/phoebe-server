"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from ..config import config
from .. import database
from ..auth import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user,
)

router = APIRouter()


# -----------------------
# Request/response models
# -----------------------

class AuthConfigResponse(BaseModel):
    mode: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str


# ---------
# Endpoints
# ---------

@router.get("/config", response_model=AuthConfigResponse)
async def auth_config():
    """Discovery endpoint: returns the server's auth mode. No auth required."""
    return {"mode": config.auth.mode}


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """Register a new user (jwt mode only)."""
    if config.auth.mode != "jwt":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration is only available in jwt auth mode",
        )

    if not req.email or not req.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    hashed = hash_password(req.password)
    user = database.create_user(
        email=req.email,
        hashed_password=hashed,
        first_name=req.first_name,
        last_name=req.last_name,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    full_name = f"{user['first_name']} {user['last_name']}".strip()
    token = create_access_token({
        "sub": str(user["id"]),
        "email": user["email"],
        "full_name": full_name,
        "role": user["role"],
    })

    return {
        "access_token": token,
        "user": {
            "user_id": str(user["id"]),
            "email": user["email"],
            "full_name": full_name,
            "role": user["role"],
        },
    }


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate and get a JWT (jwt mode only)."""
    if config.auth.mode != "jwt":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Login is only available in jwt auth mode",
        )

    user = database.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    full_name = f"{user['first_name']} {user['last_name']}".strip()
    token = create_access_token({
        "sub": str(user["id"]),
        "email": user["email"],
        "full_name": full_name,
        "role": user["role"],
    })

    return {
        "access_token": token,
        "user": {
            "user_id": str(user["id"]),
            "email": user["email"],
            "full_name": full_name,
            "role": user["role"],
        },
    }


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    """Get current user info from token (jwt/external modes)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not available in current auth mode",
        )
    return user
