"""V1 API router — mounts all endpoint sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, menus, customers, orders, broadcasts, webhooks, public, ws

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(menus.router)
api_router.include_router(customers.router)
api_router.include_router(orders.router)
api_router.include_router(broadcasts.router)
api_router.include_router(webhooks.router)
api_router.include_router(public.router)
api_router.include_router(ws.router)
