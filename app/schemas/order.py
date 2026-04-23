"""Schemas for orders (kitchen console + consumer app)."""

from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.order import OrderStatus, PaymentStatus


# ── Consumer-facing ──

class OrderItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = 1


class OrderCreate(BaseModel):
    """Submitted by the consumer app after payment."""
    kitchen_id: UUID
    menu_id: UUID
    customer_phone: str
    customer_name: str | None = None
    delivery_address: str | None = None
    notes: str | None = None
    items: list[OrderItemCreate]
    broadcast_ref: UUID | None = None  # attribution


# ── Kitchen console ──

class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ── Responses ──

class OrderItemOut(BaseModel):
    id: UUID
    item_name: str
    unit_price: float
    quantity: int
    subtotal: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: UUID
    kitchen_id: UUID
    customer_phone: str
    customer_name: str | None
    delivery_address: str | None
    notes: str | None
    subtotal: float
    total_amount: float
    payment_status: PaymentStatus
    status: OrderStatus
    items: list[OrderItemOut]
    broadcast_id: UUID | None
    created_at: datetime
    accepted_at: datetime | None
    prep_started_at: datetime | None
    ready_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
