"""Public endpoints — consumer-facing menu view and checkout initiation."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.menu import MenuOut
from app.services import menu_service, payment_service

router = APIRouter(prefix="/public", tags=["public"])


class CheckoutItemRequest(BaseModel):
    menu_item_id: UUID
    name: str
    price: float
    quantity: int


class CheckoutRequest(BaseModel):
    kitchen_id: UUID
    menu_id: UUID
    customer_phone: str
    customer_name: str | None = None
    delivery_address: str | None = None
    notes: str | None = None
    broadcast_ref: UUID | None = None
    items: list[CheckoutItemRequest]


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str


@router.get("/menu/{kitchen_id}/{menu_id}", response_model=MenuOut)
async def get_public_menu(
    kitchen_id: UUID,
    menu_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Deep link lands here — shows the published menu.
    No auth required.
    """
    return await menu_service.get_public_menu(db, kitchen_id, menu_id)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(payload: CheckoutRequest):
    """
    Consumer selects items and hits 'Pay'.
    Creates a Stripe Checkout Session and returns the redirect URL.
    """
    items_for_stripe = [
        {"name": item.name, "price": item.price, "quantity": item.quantity}
        for item in payload.items
    ]

    result = await payment_service.create_checkout_session(
        kitchen_id=payload.kitchen_id,
        menu_id=payload.menu_id,
        items=items_for_stripe,
        customer_phone=payload.customer_phone,
        customer_name=payload.customer_name,
        delivery_address=payload.delivery_address,
        notes=payload.notes,
        broadcast_ref=payload.broadcast_ref,
    )
    return CheckoutResponse(**result)
