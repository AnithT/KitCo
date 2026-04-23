"""Schemas for broadcast endpoints."""

from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.broadcast import BroadcastChannel


class BroadcastCreate(BaseModel):
    menu_id: UUID
    channel: BroadcastChannel = BroadcastChannel.WHATSAPP
    message_template: str | None = None  # uses default if None


class BroadcastOut(BaseModel):
    id: UUID
    kitchen_id: UUID
    menu_id: UUID | None
    channel: BroadcastChannel
    total_recipients: int
    delivered_count: int
    read_count: int
    clicked_count: int
    sent_at: datetime

    model_config = {"from_attributes": True}
