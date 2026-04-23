"""Auth endpoints — kitchen registration and login."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.models.kitchen import Kitchen
from app.schemas.auth import KitchenRegister, KitchenLogin, TokenResponse, TokenRefresh

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: KitchenRegister, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(
        select(Kitchen).where(Kitchen.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    kitchen = Kitchen(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        phone=payload.phone,
        address=payload.address,
        timezone=payload.timezone,
    )
    db.add(kitchen)
    await db.flush()

    token_data = {"sub": str(kitchen.id), "email": kitchen.email}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["email", "password"],
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "password": {"type": "string"},
                        },
                    },
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "required": ["username", "password"],
                        "properties": {
                            "grant_type": {"type": "string", "enum": ["password"]},
                            "username": {"type": "string", "description": "Kitchen email"},
                            "password": {"type": "string"},
                            "scope": {"type": "string"},
                            "client_id": {"type": "string"},
                            "client_secret": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
)
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid JSON body")
        email = body.get("email") or body.get("username")
        password = body.get("password")

    if not email or not password:
        raise HTTPException(status_code=422, detail="Email and password are required")

    result = await db.execute(
        select(Kitchen).where(Kitchen.email == email)
    )
    kitchen = result.scalar_one_or_none()
    if not kitchen or not verify_password(password, kitchen.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not kitchen.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token_data = {"sub": str(kitchen.id), "email": kitchen.email}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: TokenRefresh, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Verify kitchen still exists and is active
    result = await db.execute(select(Kitchen).where(Kitchen.id == data["sub"]))
    kitchen = result.scalar_one_or_none()
    if not kitchen or not kitchen.is_active:
        raise HTTPException(status_code=401, detail="Account not found or inactive")

    token_data = {"sub": str(kitchen.id), "email": kitchen.email}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
