"""Import all models so SQLAlchemy metadata is populated."""

from app.models.kitchen import Kitchen  # noqa: F401
from app.models.menu import Menu, MenuItem, MenuStatus  # noqa: F401
from app.models.customer import Customer, ChannelPreference  # noqa: F401
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus  # noqa: F401
from app.models.broadcast import (  # noqa: F401
    Broadcast, BroadcastRecipient, BroadcastChannel, RecipientStatus,
)