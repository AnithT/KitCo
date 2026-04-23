"""Order service — handles order creation, status transitions, and stock."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.menu import MenuItem, Menu, MenuStatus
from app.schemas.order import OrderCreate, OrderStatusUpdate
from app.services import customer_service


# ── Valid status transitions ──
VALID_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELLED],
    OrderStatus.ACCEPTED: [OrderStatus.IN_PREP, OrderStatus.CANCELLED],
    OrderStatus.IN_PREP: [OrderStatus.READY],
    OrderStatus.READY: [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.COMPLETED],
    OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.COMPLETED],
    # terminal states — no transitions
    OrderStatus.COMPLETED: [],
    OrderStatus.REJECTED: [],
    OrderStatus.CANCELLED: [],
}

# Map status to its timestamp field
STATUS_TIMESTAMP_MAP: dict[OrderStatus, str] = {
    OrderStatus.ACCEPTED: "accepted_at",
    OrderStatus.IN_PREP: "prep_started_at",
    OrderStatus.READY: "ready_at",
    OrderStatus.COMPLETED: "completed_at",
}


async def create_order(db: AsyncSession, payload: OrderCreate) -> Order:
    """
    Called after payment succeeds. Validates menu items,
    calculates totals, decrements stock, creates the order.
    """
    # 1. Verify menu is published
    menu_result = await db.execute(
        select(Menu)
        .options(selectinload(Menu.items))
        .where(
            Menu.id == payload.menu_id,
            Menu.kitchen_id == payload.kitchen_id,
            Menu.status == MenuStatus.PUBLISHED,
        )
    )
    menu = menu_result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found or not published")

    # Build a lookup of available items
    available_items: dict[uuid.UUID, MenuItem] = {
        item.id: item for item in menu.items if item.is_available
    }

    # 2. Validate items and compute totals
    order_items: list[OrderItem] = []
    subtotal = 0.0

    for line in payload.items:
        menu_item = available_items.get(line.menu_item_id)
        if not menu_item:
            raise HTTPException(
                status_code=400,
                detail=f"Item {line.menu_item_id} is not available",
            )
        # Stock check
        if menu_item.stock_quantity is not None:
            if menu_item.stock_quantity < line.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for '{menu_item.name}'. "
                           f"Available: {menu_item.stock_quantity}",
                )
            menu_item.stock_quantity -= line.quantity
            if menu_item.stock_quantity == 0:
                menu_item.is_available = False

        line_subtotal = float(menu_item.price) * line.quantity
        subtotal += line_subtotal

        order_items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                item_name=menu_item.name,
                unit_price=float(menu_item.price),
                quantity=line.quantity,
                subtotal=line_subtotal,
            )
        )

    # 3. Find or create customer record
    customer = await customer_service.find_or_create_by_phone(
        db, payload.kitchen_id, payload.customer_phone, payload.customer_name
    )

    # 4. Create order
    order = Order(
        kitchen_id=payload.kitchen_id,
        customer_id=customer.id,
        customer_phone=payload.customer_phone,
        customer_name=payload.customer_name,
        delivery_address=payload.delivery_address,
        notes=payload.notes,
        subtotal=subtotal,
        total_amount=subtotal,  # can add tax/delivery fees later
        payment_status=PaymentStatus.PAID,  # webhook already confirmed
        status=OrderStatus.PENDING,
        broadcast_id=payload.broadcast_ref,
    )
    order.items = order_items
    db.add(order)

    # Increment customer order count
    customer.total_orders += 1

    await db.flush()

    # Reload with items
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    return result.scalar_one()


async def get_order(
    db: AsyncSession, order_id: uuid.UUID, kitchen_id: uuid.UUID
) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.kitchen_id == kitchen_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def list_orders(
    db: AsyncSession,
    kitchen_id: uuid.UUID,
    status_filter: OrderStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Order]:
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.kitchen_id == kitchen_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status_filter:
        query = query.where(Order.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_order_status(
    db: AsyncSession,
    order_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    payload: OrderStatusUpdate,
) -> Order:
    order = await get_order(db, order_id, kitchen_id)

    # Validate transition
    allowed = VALID_TRANSITIONS.get(order.status, [])
    if payload.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{order.status.value}' to '{payload.status.value}'. "
                   f"Allowed: {[s.value for s in allowed]}",
        )

    order.status = payload.status

    # Set the corresponding timestamp
    ts_field = STATUS_TIMESTAMP_MAP.get(payload.status)
    if ts_field:
        setattr(order, ts_field, datetime.now(timezone.utc))

    await db.flush()
    return order


async def get_order_public(db: AsyncSession, order_id: uuid.UUID, phone: str) -> Order:
    """Public status lookup — authenticate by order id + phone."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.customer_phone == phone)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
