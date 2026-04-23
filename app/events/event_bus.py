"""
Lightweight in-process event bus.

Services emit events (e.g. order.created, order.status_changed).
Handlers subscribe to event names and run side effects
(notifications, analytics ingestion, etc.) without coupling services.

In production, swap this for a proper message broker (RabbitMQ / SQS).
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Registry: event_name → list of async handler functions
_handlers: dict[str, list[Callable[..., Coroutine]]] = defaultdict(list)


def on(event_name: str):
    """Decorator to register an async handler for an event."""
    def decorator(func: Callable[..., Coroutine]):
        _handlers[event_name].append(func)
        return func
    return decorator


async def emit(event_name: str, payload: dict[str, Any]) -> None:
    """Fire all handlers for the given event. Errors are logged, not raised."""
    handlers = _handlers.get(event_name, [])
    for handler in handlers:
        try:
            await handler(payload)
        except Exception:
            logger.exception(
                "Event handler %s failed for event '%s'",
                handler.__name__, event_name,
            )


# ── Predefined event names ──

ORDER_CREATED = "order.created"
ORDER_STATUS_CHANGED = "order.status_changed"
BROADCAST_CREATED = "broadcast.created"
BROADCAST_DELIVERED = "broadcast.delivered"
PAYMENT_RECEIVED = "payment.received"
