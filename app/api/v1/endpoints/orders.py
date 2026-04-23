"""Order endpoints — kitchen console views + consumer-facing order tracking."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_kitchen
from app.models.kitchen import Kitchen
from app.models.order import OrderStatus
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


# ── Kitchen console (authenticated) ──


@router.get("/", response_model=list[OrderOut])
async def list_orders(
    status: OrderStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.list_orders(db, kitchen.id, status, skip, limit)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: UUID,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.get_order(db, order_id, kitchen.id)


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    """Kitchen accepts/rejects/advances order through prep stages."""
    return await order_service.update_order_status(db, order_id, kitchen.id, payload)


# ── Consumer-facing (public) ──


@router.post("/", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Called after payment confirmation — creates the order."""
    return await order_service.create_order(db, payload)


@router.get("/track/{order_id}", response_model=OrderOut)
async def track_order(
    order_id: UUID,
    phone: str = Query(..., description="Customer phone for verification"),
    db: AsyncSession = Depends(get_db),
):
    """Public order tracking — no auth, verified by phone number."""
    return await order_service.get_order_public(db, order_id, phone)
