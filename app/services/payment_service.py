"""Payment service — Stripe Checkout integration."""

import uuid
import stripe
from fastapi import HTTPException

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_checkout_session(
    kitchen_id: uuid.UUID,
    menu_id: uuid.UUID,
    items: list[dict],
    customer_phone: str,
    customer_name: str | None = None,
    delivery_address: str | None = None,
    notes: str | None = None,
    broadcast_ref: uuid.UUID | None = None,
) -> dict:
    """
    Creates a Stripe Checkout Session.
    `items` is a list of dicts: [{"name": str, "price": float, "quantity": int}]
    Returns {session_id, checkout_url} for the client to redirect to.
    """
    line_items = [
        {
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": item["name"]},
                "unit_amount": int(item["price"] * 100),  # pence
            },
            "quantity": item["quantity"],
        }
        for item in items
    ]

    metadata = {
        "kitchen_id": str(kitchen_id),
        "menu_id": str(menu_id),
        "customer_phone": customer_phone,
        "customer_name": customer_name or "",
        "delivery_address": delivery_address or "",
        "notes": notes or "",
        "broadcast_ref": str(broadcast_ref) if broadcast_ref else "",
    }

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            metadata=metadata,
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Payment provider error: {str(e)}")

    return {"session_id": session.id, "checkout_url": session.url}


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and parse a Stripe webhook event."""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")
