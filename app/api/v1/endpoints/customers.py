"""Customer management endpoints — kitchen console."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_kitchen
from app.models.kitchen import Kitchen
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerOut, CustomerBulkImport,
)
from app.services import customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=CustomerOut, status_code=201)
async def create_customer(
    payload: CustomerCreate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.create_customer(db, kitchen.id, payload)


@router.post("/bulk-import")
async def bulk_import(
    payload: CustomerBulkImport,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.bulk_import_customers(db, kitchen.id, payload.customers)


@router.get("/", response_model=list[CustomerOut])
async def list_customers(
    opted_in_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.list_customers(
        db, kitchen.id, opted_in_only, skip, limit
    )


@router.get("/count")
async def customer_count(
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    count = await customer_service.get_opted_in_count(db, kitchen.id)
    return {"opted_in_count": count}


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: UUID,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.get_customer(db, customer_id, kitchen.id)


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    kitchen: Kitchen = Depends(get_current_kitchen),
    db: AsyncSession = Depends(get_db),
):
    return await customer_service.update_customer(db, customer_id, kitchen.id, payload)
