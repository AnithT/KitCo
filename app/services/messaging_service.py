"""Messaging service — sends WhatsApp/SMS via Twilio."""

from twilio.rest import Client

from app.core.config import settings
from app.models.broadcast import BroadcastChannel

_client: Client | None = None


def _get_twilio_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def send_message(
    to_phone: str,
    body: str,
    channel: BroadcastChannel,
    status_callback_url: str | None = None,
) -> str:
    """
    Send a single message. Returns the Twilio Message SID.
    Called by the Celery worker, not directly from the API.
    """
    client = _get_twilio_client()
    callback = status_callback_url or settings.TWILIO_STATUS_CALLBACK_URL

    if channel == BroadcastChannel.WHATSAPP:
        from_number = settings.TWILIO_WHATSAPP_FROM
        to_number = f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone
    else:
        from_number = settings.TWILIO_SMS_FROM
        to_number = to_phone

    message = client.messages.create(
        body=body,
        from_=from_number,
        to=to_number,
        status_callback=callback,
    )
    return message.sid


def send_order_notification(to_phone: str, order_id: str, status: str) -> str:
    """Send an order status update to a customer via WhatsApp."""
    status_labels = {
        "accepted": "✅ Your order has been accepted and will be prepared shortly!",
        "in_prep": "👨‍🍳 Your order is being prepared now!",
        "ready": "🎉 Your order is ready!",
        "out_for_delivery": "🚗 Your order is on its way!",
        "completed": "✨ Your order has been delivered. Enjoy your meal!",
        "rejected": "😔 Sorry, the kitchen was unable to accept your order. You will be refunded.",
    }
    body = status_labels.get(status, f"Order update: {status}")
    tracking_url = f"{settings.CLIENT_APP_BASE_URL}/track/{order_id}"
    body += f"\n\nTrack your order: {tracking_url}"

    return send_message(to_phone, body, BroadcastChannel.WHATSAPP)
