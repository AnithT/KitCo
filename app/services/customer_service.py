"""Customer service — manage opted-in customer lists."""

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


async def create_customer(
    db: AsyncSession, kitchen_id: uuid.UUID, payload: CustomerCreate
) -> Customer:
    # check duplicate phone per kitchen
    existing = await db.execute(
        select(Customer).where(
            Customer.kitchen_id == kitchen_id, Customer.phone == payload.phone
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Customer with this phone already exists")

    customer = Customer(kitchen_id=kitchen_id, **payload.model_dump())
    db.add(customer)
    await db.flush()
    return customer


async def bulk_import_customers(
    db: AsyncSession, kitchen_id: uuid.UUID, customers_data: list[CustomerCreate]
) -> dict:
    created = 0
    skipped = 0
    for data in customers_data:
        existing = await db.execute(
            select(Customer).where(
                Customer.kitchen_id == kitchen_id, Customer.phone == data.phone
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        db.add(Customer(kitchen_id=kitchen_id, **data.model_dump()))
        created += 1

    await db.flush()
    return {"created": created, "skipped": skipped, "total": created + skipped}


async def list_customers(
    db: AsyncSession,
    kitchen_id: uuid.UUID,
    opted_in_only: bool = True,
    skip: int = 0,
    limit: int = 50,
) -> list[Customer]:
    query = (
        select(Customer)
        .where(Customer.kitchen_id == kitchen_id)
        .order_by(Customer.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if opted_in_only:
        query = query.where(Customer.is_opted_in == True)  # noqa: E712
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_customer(
    db: AsyncSession, customer_id: uuid.UUID, kitchen_id: uuid.UUID
) -> Customer:
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.kitchen_id == kitchen_id
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


async def update_customer(
    db: AsyncSession,
    customer_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    payload: CustomerUpdate,
) -> Customer:
    customer = await get_customer(db, customer_id, kitchen_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await db.flush()
    return customer


async def find_or_create_by_phone(
    db: AsyncSession, kitchen_id: uuid.UUID, phone: str, name: str | None = None
) -> Customer:
    """Used during ordering — find existing customer or create a new one."""
    result = await db.execute(
        select(Customer).where(
            Customer.kitchen_id == kitchen_id, Customer.phone == phone
        )
    )
    customer = result.scalar_one_or_none()
    if customer:
        return customer

    customer = Customer(kitchen_id=kitchen_id, phone=phone, name=name)
    db.add(customer)
    await db.flush()
    return customer


async def get_opted_in_count(db: AsyncSession, kitchen_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(Customer.id)).where(
            Customer.kitchen_id == kitchen_id, Customer.is_opted_in == True  # noqa
        )
    )
    return result.scalar_one()
