"""Schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr


class KitchenRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    address: str | None = None
    timezone: str = "UTC"


class KitchenLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str
