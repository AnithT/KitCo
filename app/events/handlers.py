"""
Event handlers — subscribe to events and run side effects.
Import this module at app startup to register handlers.
"""

import logging
from app.events.event_bus import on, ORDER_CREATED, ORDER_STATUS_CHANGED

logger = logging.getLogger(__name__)


@on(ORDER_CREATED)
async def notify_kitchen_new_order(payload: dict):
    """Send push / sound notification to kitchen console via WebSocket."""
    order_id = payload.get("order_id")
    kitchen_id = payload.get("kitchen_id")
    logger.info("New order %s for kitchen %s — notify console", order_id, kitchen_id)
    # TODO: push via WebSocket manager
    # await ws_manager.broadcast_to_kitchen(kitchen_id, {"type": "new_order", ...})


@on(ORDER_STATUS_CHANGED)
async def notify_customer_status_change(payload: dict):
    """Send WhatsApp status update to customer."""
    order_id = payload.get("order_id")
    phone = payload.get("customer_phone")
    new_status = payload.get("new_status")
    logger.info(
        "Order %s → %s — sending notification to %s", order_id, new_status, phone
    )
    # In production:
    # from app.services.messaging_service import send_order_notification
    # send_order_notification(phone, str(order_id), new_status)
