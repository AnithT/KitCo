"""Menu service — create, update, publish menus and manage items."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.menu import Menu, MenuItem, MenuStatus
from app.schemas.menu import MenuCreate, MenuUpdate, MenuItemCreate, MenuItemUpdate


async def create_menu(
    db: AsyncSession, kitchen_id: uuid.UUID, payload: MenuCreate
) -> Menu:
    menu = Menu(
        kitchen_id=kitchen_id,
        title=payload.title,
        date=payload.date,
        status=MenuStatus.DRAFT,
    )
    db.add(menu)
    await db.flush()

    for item_data in payload.items:
        item = MenuItem(menu_id=menu.id, **item_data.model_dump())
        db.add(item)

    await db.flush()
    # reload with items
    result = await db.execute(
        select(Menu).options(selectinload(Menu.items)).where(Menu.id == menu.id)
    )
    return result.scalar_one()


async def get_menu(db: AsyncSession, menu_id: uuid.UUID, kitchen_id: uuid.UUID) -> Menu:
    result = await db.execute(
        select(Menu)
        .options(selectinload(Menu.items))
        .where(Menu.id == menu_id, Menu.kitchen_id == kitchen_id)
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    return menu


async def list_menus(
    db: AsyncSession,
    kitchen_id: uuid.UUID,
    menu_date: date | None = None,
    status_filter: MenuStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Menu]:
    query = (
        select(Menu)
        .options(selectinload(Menu.items))
        .where(Menu.kitchen_id == kitchen_id)
        .order_by(Menu.date.desc())
        .offset(skip)
        .limit(limit)
    )
    if menu_date:
        query = query.where(Menu.date == menu_date)
    if status_filter:
        query = query.where(Menu.status == status_filter)

    result = await db.execute(query)
    return list(result.scalars().all())


async def update_menu(
    db: AsyncSession, menu_id: uuid.UUID, kitchen_id: uuid.UUID, payload: MenuUpdate
) -> Menu:
    menu = await get_menu(db, menu_id, kitchen_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(menu, field, value)
    await db.flush()
    return menu


async def publish_menu(
    db: AsyncSession, menu_id: uuid.UUID, kitchen_id: uuid.UUID
) -> Menu:
    menu = await get_menu(db, menu_id, kitchen_id)
    if not menu.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish an empty menu. Add items first.",
        )
    menu.status = MenuStatus.PUBLISHED
    await db.flush()
    return menu


async def delete_menu(
    db: AsyncSession, menu_id: uuid.UUID, kitchen_id: uuid.UUID
) -> None:
    menu = await get_menu(db, menu_id, kitchen_id)
    await db.delete(menu)
    await db.flush()


# ── Menu Items ──


async def add_menu_item(
    db: AsyncSession, menu_id: uuid.UUID, kitchen_id: uuid.UUID, payload: MenuItemCreate
) -> MenuItem:
    # verify menu belongs to kitchen
    await get_menu(db, menu_id, kitchen_id)
    item = MenuItem(menu_id=menu_id, **payload.model_dump())
    db.add(item)
    await db.flush()
    return item


async def update_menu_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    payload: MenuItemUpdate,
) -> MenuItem:
    result = await db.execute(
        select(MenuItem)
        .join(Menu)
        .where(MenuItem.id == item_id, Menu.kitchen_id == kitchen_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    return item


async def delete_menu_item(
    db: AsyncSession, item_id: uuid.UUID, kitchen_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(MenuItem)
        .join(Menu)
        .where(MenuItem.id == item_id, Menu.kitchen_id == kitchen_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    await db.delete(item)
    await db.flush()


async def get_public_menu(db: AsyncSession, kitchen_id: uuid.UUID, menu_id: uuid.UUID) -> Menu:
    """Public endpoint — only returns published menus with available items."""
    result = await db.execute(
        select(Menu)
        .options(selectinload(Menu.items))
        .where(
            Menu.id == menu_id,
            Menu.kitchen_id == kitchen_id,
            Menu.status == MenuStatus.PUBLISHED,
        )
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found or not published")
    # filter to available items only
    menu.items = [i for i in menu.items if i.is_available]
    return menu
