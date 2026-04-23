"""Webhook endpoints — Stripe payment confirmation + Twilio status callbacks."""

import uuid

from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.broadcast import RecipientStatus
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services import payment_service, order_service, broadcast_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# ── Twilio status → RecipientStatus mapping ──
TWILIO_STATUS_MAP = {
    "sent": RecipientStatus.SENT,
    "delivered": RecipientStatus.DELIVERED,
    "read": RecipientStatus.READ,
    "failed": RecipientStatus.FAILED,
    "undelivered": RecipientStatus.FAILED,
}


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stripe sends checkout.session.completed when payment succeeds.
    We extract order metadata and create the order.
    """
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    event = payment_service.construct_webhook_event(payload, stripe_signature)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})

        # Retrieve line items from Stripe to rebuild order items
        import stripe
        line_items = stripe.checkout.Session.list_line_items(session["id"])

        order_items = []
        for li in line_items.get("data", []):
            order_items.append(
                OrderItemCreate(
                    menu_item_id=uuid.UUID(li["metadata"]["menu_item_id"])
                    if li.get("metadata", {}).get("menu_item_id")
                    else uuid.uuid4(),  # fallback
                    quantity=li["quantity"],
                )
            )

        order_payload = OrderCreate(
            kitchen_id=uuid.UUID(metadata["kitchen_id"]),
            menu_id=uuid.UUID(metadata["menu_id"]),
            customer_phone=metadata["customer_phone"],
            customer_name=metadata.get("customer_name") or None,
            delivery_address=metadata.get("delivery_address") or None,
            notes=metadata.get("notes") or None,
            items=order_items,
            broadcast_ref=uuid.UUID(metadata["broadcast_ref"])
            if metadata.get("broadcast_ref")
            else None,
        )

        await order_service.create_order(db, order_payload)

    return {"status": "ok"}


@router.post("/twilio/status")
async def twilio_status_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Twilio calls this URL for every message status change.
    We update the BroadcastRecipient record.
    """
    form = await request.form()
    message_sid = form.get("MessageSid", "")
    message_status = form.get("MessageStatus", "")

    new_status = TWILIO_STATUS_MAP.get(message_status)
    if new_status and message_sid:
        await broadcast_service.update_recipient_status(db, message_sid, new_status)

    return {"status": "ok"}
