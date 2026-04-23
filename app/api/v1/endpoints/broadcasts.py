"""Broadcast endpoints — trigger and monitor menu sends."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_kitchen
from app.models.kitchen import Kitchen
from app.schemas.broadcast import BroadcastCreate, BroadcastOut
from app.services import broadcast_service

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


@router.post("/", response_model=BroadcastOut, status_code=201)
async def create_broadcast(
    payload: BroadcastCreate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    """Publish a menu broadcast to all opted-in customers."""
    return await broadcast_service.create_broadcast(db, kitchen.id, payload)


@router.get("/", response_model=list[BroadcastOut])
async def list_broadcasts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await broadcast_service.list_broadcasts(db, kitchen.id, skip, limit)


@router.get("/{broadcast_id}", response_model=BroadcastOut)
async def get_broadcast(
    broadcast_id: UUID,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await broadcast_service.get_broadcast(db, broadcast_id, kitchen.id)
