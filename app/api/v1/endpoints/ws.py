"""WebSocket endpoints for real-time order updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.websocket import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/kitchen/{kitchen_id}")
async def kitchen_ws(websocket: WebSocket, kitchen_id: str):
    """
    Kitchen console connects here for live order feed.
    In production, authenticate via token query param.
    """
    await ws_manager.connect_kitchen(websocket, kitchen_id)
    try:
        while True:
            # Keep connection alive; console can also send acks
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_kitchen(websocket, kitchen_id)


@router.websocket("/ws/order/{order_id}")
async def order_tracking_ws(websocket: WebSocket, order_id: str):
    """
    Customer tracking page connects here for live status updates.
    """
    await ws_manager.connect_order(websocket, order_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_order(websocket, order_id)
