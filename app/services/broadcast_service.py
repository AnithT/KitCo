"""Broadcast service — create broadcasts and queue messages."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.core.config import settings
from app.models.broadcast import (
    Broadcast, BroadcastRecipient, BroadcastChannel, RecipientStatus,
)
from app.models.customer import Customer, ChannelPreference
from app.models.menu import Menu, MenuStatus
from app.schemas.broadcast import BroadcastCreate


def _build_default_message(menu: Menu, broadcast_id: uuid.UUID) -> str:
    """Build the WhatsApp/SMS message body with a deep link."""
    items_text = "\n".join(
        f"• {item.name} — £{item.price:.2f}" for item in menu.items if item.is_available
    )
    deep_link = (
        f"{settings.CLIENT_APP_BASE_URL}/order/{menu.kitchen_id}"
        f"?menu={menu.id}&ref={broadcast_id}"
    )
    return (
        f"🍽️ *{menu.title}* — {menu.date.strftime('%A, %d %B')}\n\n"
        f"{items_text}\n\n"
        f"👉 Tap to order: {deep_link}"
    )


async def create_broadcast(
    db: AsyncSession, kitchen_id: uuid.UUID, payload: BroadcastCreate
) -> Broadcast:
    # 1. Verify menu is published
    result = await db.execute(
        select(Menu)
        .options(selectinload(Menu.items))
        .where(
            Menu.id == payload.menu_id,
            Menu.kitchen_id == kitchen_id,
            Menu.status == MenuStatus.PUBLISHED,
        )
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found or not published")

    # 2. Get opted-in customers matching the channel
    channel = payload.channel
    query = select(Customer).where(
        Customer.kitchen_id == kitchen_id,
        Customer.is_opted_in == True,  # noqa: E712
    )
    if channel == BroadcastChannel.WHATSAPP:
        query = query.where(
            Customer.channel_preference.in_([
                ChannelPreference.WHATSAPP, ChannelPreference.BOTH
            ])
        )
    else:
        query = query.where(
            Customer.channel_preference.in_([
                ChannelPreference.SMS, ChannelPreference.BOTH
            ])
        )
    cust_result = await db.execute(query)
    customers = list(cust_result.scalars().all())

    if not customers:
        raise HTTPException(status_code=400, detail="No opted-in customers for this channel")

    # 3. Create broadcast record
    broadcast = Broadcast(
        kitchen_id=kitchen_id,
        menu_id=menu.id,
        channel=channel,
        total_recipients=len(customers),
    )
    db.add(broadcast)
    await db.flush()

    # 4. Build message
    message = payload.message_template or _build_default_message(menu, broadcast.id)
    broadcast.message_template = message

    # 5. Create recipient records (all start as QUEUED)
    recipients = []
    for cust in customers:
        recipient = BroadcastRecipient(
            broadcast_id=broadcast.id,
            customer_id=cust.id,
            phone=cust.phone,
            status=RecipientStatus.QUEUED,
        )
        recipients.append(recipient)
        db.add(recipient)

    await db.flush()

    # 6. Dispatch to background worker
    #    In production this calls Celery: send_broadcast_messages.delay(str(broadcast.id))
    #    For now we just mark the broadcast as created — the Celery task is defined separately.

    return broadcast


async def get_broadcast(
    db: AsyncSession, broadcast_id: uuid.UUID, kitchen_id: uuid.UUID
) -> Broadcast:
    result = await db.execute(
        select(Broadcast).where(
            Broadcast.id == broadcast_id, Broadcast.kitchen_id == kitchen_id
        )
    )
    broadcast = result.scalar_one_or_none()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return broadcast


async def list_broadcasts(
    db: AsyncSession, kitchen_id: uuid.UUID, skip: int = 0, limit: int = 20
) -> list[Broadcast]:
    result = await db.execute(
        select(Broadcast)
        .where(Broadcast.kitchen_id == kitchen_id)
        .order_by(Broadcast.sent_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_recipient_status(
    db: AsyncSession,
    twilio_message_sid: str,
    new_status: RecipientStatus,
) -> None:
    """Called by the Twilio status callback webhook."""
    result = await db.execute(
        select(BroadcastRecipient).where(
            BroadcastRecipient.twilio_message_sid == twilio_message_sid
        )
    )
    recipient = result.scalar_one_or_none()
    if not recipient:
        return  # ignore unknown SIDs

    now = datetime.now(timezone.utc)
    recipient.status = new_status

    if new_status == RecipientStatus.DELIVERED:
        recipient.delivered_at = now
    elif new_status == RecipientStatus.READ:
        recipient.read_at = now

    # Update aggregate counts on the broadcast
    broadcast_result = await db.execute(
        select(Broadcast).where(Broadcast.id == recipient.broadcast_id)
    )
    broadcast = broadcast_result.scalar_one_or_none()
    if broadcast:
        if new_status == RecipientStatus.DELIVERED:
            broadcast.delivered_count += 1
        elif new_status == RecipientStatus.READ:
            broadcast.read_count += 1

    await db.flush()
