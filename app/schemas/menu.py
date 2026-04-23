"""Schemas for menu CRUD."""

from __future__ import annotations
from datetime import date as date_type
from uuid import UUID
from pydantic import BaseModel
from app.models.menu import MenuStatus


# ── MenuItem ──

class MenuItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    cost: float | None = None
    image_url: str | None = None
    category: str | None = None
    stock_quantity: int | None = None
    is_available: bool = True
    prep_time_minutes: int | None = None
    sort_order: int = 0


class MenuItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    cost: float | None = None
    image_url: str | None = None
    category: str | None = None
    stock_quantity: int | None = None
    is_available: bool | None = None
    prep_time_minutes: int | None = None
    sort_order: int | None = None


class MenuItemOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    price: float
    cost: float | None
    image_url: str | None
    category: str | None
    stock_quantity: int | None
    is_available: bool
    prep_time_minutes: int | None
    sort_order: int

    model_config = {"from_attributes": True}


# ── Menu ──

class MenuCreate(BaseModel):
    title: str = "Daily Menu"
    date: date_type
    items: list[MenuItemCreate] = []


class MenuUpdate(BaseModel):
    title: str | None = None
    date: date_type | None = None
    status: MenuStatus | None = None


class MenuOut(BaseModel):
    id: UUID
    kitchen_id: UUID
    title: str
    date: date_type
    status: MenuStatus
    items: list[MenuItemOut] = []

    model_config = {"from_attributes": True}
