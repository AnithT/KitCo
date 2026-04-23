"""Schemas for customer management."""

from uuid import UUID
from pydantic import BaseModel
from app.models.customer import ChannelPreference


class CustomerCreate(BaseModel):
    phone: str
    name: str | None = None
    address: str | None = None
    channel_preference: ChannelPreference = ChannelPreference.WHATSAPP


class CustomerUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    channel_preference: ChannelPreference | None = None
    is_opted_in: bool | None = None


class CustomerOut(BaseModel):
    id: UUID
    kitchen_id: UUID
    phone: str
    name: str | None
    address: str | None
    channel_preference: ChannelPreference
    is_opted_in: bool
    total_orders: int

    model_config = {"from_attributes": True}


class CustomerBulkImport(BaseModel):
    """CSV-style bulk import."""
    customers: list[CustomerCreate]
