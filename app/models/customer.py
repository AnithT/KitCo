"""Customer — opted-in recipient for menu broadcasts."""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChannelPreference(str, PyEnum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    BOTH = "both"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kitchen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), index=True
    )
    phone: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    channel_preference: Mapped[ChannelPreference] = mapped_column(
        Enum(ChannelPreference), default=ChannelPreference.WHATSAPP
    )
    is_opted_in: Mapped[bool] = mapped_column(Boolean, default=True)
    total_orders: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    kitchen = relationship("Kitchen", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

    __table_args__ = (
        # A phone number is unique per kitchen
        {"sqlite_autoincrement": True},
    )
