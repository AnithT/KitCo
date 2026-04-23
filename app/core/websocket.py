"""
WebSocket connection manager.

Kitchen consoles connect to receive real-time order updates.
Customer tracking pages connect to receive status changes for their order.
"""

import json
import uuid
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by kitchen_id or order_id."""

    def __init__(self):
        # kitchen_id → set of WebSocket connections (kitchen console)
        self._kitchen_connections: dict[str, set[WebSocket]] = defaultdict(set)
        # order_id → set of WebSocket connections (customer tracking)
        self._order_connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect_kitchen(self, websocket: WebSocket, kitchen_id: str):
        await websocket.accept()
        self._kitchen_connections[kitchen_id].add(websocket)
        logger.info("Kitchen %s console connected. Total: %d",
                     kitchen_id, len(self._kitchen_connections[kitchen_id]))

    async def connect_order(self, websocket: WebSocket, order_id: str):
        await websocket.accept()
        self._order_connections[order_id].add(websocket)

    def disconnect_kitchen(self, websocket: WebSocket, kitchen_id: str):
        self._kitchen_connections[kitchen_id].discard(websocket)

    def disconnect_order(self, websocket: WebSocket, order_id: str):
        self._order_connections[order_id].discard(websocket)

    async def broadcast_to_kitchen(self, kitchen_id: str, data: dict):
        """Push event to all console connections for this kitchen."""
        dead = set()
        for ws in self._kitchen_connections.get(kitchen_id, set()):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.add(ws)
        self._kitchen_connections[kitchen_id] -= dead

    async def broadcast_to_order(self, order_id: str, data: dict):
        """Push status update to customer tracking page."""
        dead = set()
        for ws in self._order_connections.get(order_id, set()):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.add(ws)
        self._order_connections[order_id] -= dead


# Singleton
ws_manager = ConnectionManager()
