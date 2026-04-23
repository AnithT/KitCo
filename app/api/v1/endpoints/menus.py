"""Menu CRUD endpoints — kitchen console."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_kitchen
from app.models.kitchen import Kitchen
from app.models.menu import MenuStatus
from app.schemas.menu import (
    MenuCreate, MenuUpdate, MenuOut,
    MenuItemCreate, MenuItemUpdate, MenuItemOut,
)
from app.services import menu_service

router = APIRouter(prefix="/menus", tags=["menus"])


@router.post("/", response_model=MenuOut, status_code=201)
async def create_menu(
    payload: MenuCreate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.create_menu(db, kitchen.id, payload)


@router.get("/", response_model=list[MenuOut])
async def list_menus(
    menu_date: date | None = Query(None),
    status: MenuStatus | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.list_menus(db, kitchen.id, menu_date, status, skip, limit)


@router.get("/{menu_id}", response_model=MenuOut)
async def get_menu(
    menu_id: UUID,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.get_menu(db, menu_id, kitchen.id)


@router.patch("/{menu_id}", response_model=MenuOut)
async def update_menu(
    menu_id: UUID,
    payload: MenuUpdate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.update_menu(db, menu_id, kitchen.id, payload)


@router.post("/{menu_id}/publish", response_model=MenuOut)
async def publish_menu(
    menu_id: UUID,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.publish_menu(db, menu_id, kitchen.id)


@router.delete("/{menu_id}", status_code=204)
async def delete_menu(
    menu_id: UUID,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    await menu_service.delete_menu(db, menu_id, kitchen.id)


# ── Menu Items ──


@router.post("/{menu_id}/items", response_model=MenuItemOut, status_code=201)
async def add_item(
    menu_id: UUID,
    payload: MenuItemCreate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.add_menu_item(db, menu_id, kitchen.id, payload)


@router.patch("/items/{item_id}", response_model=MenuItemOut)
async def update_item(
    item_id: UUID,
    payload: MenuItemUpdate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.update_menu_item(db, item_id, kitchen.id, payload)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: UUID,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    await menu_service.delete_menu_item(db, item_id, kitchen.id)
