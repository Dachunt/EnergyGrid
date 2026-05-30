import asyncio
import json
import logging
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("energygrid")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.redis = None
        self.redis_url = os.getenv("REDIS_URL", "redis://energygrid-redis:6379")
        self.pubsub = None
        self._listener_task = None

    async def connect_redis(self):
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe("energygrid:broadcast")
            self._listener_task = asyncio.create_task(self._redis_listener())
            logger.info("Connected to Redis pub/sub on %s", self.redis_url)
        except Exception as e:
            logger.warning("Redis not available (%s), running in local-only mode", e)
            self.redis = None

    async def _redis_listener(self):
        while True:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._broadcast_local(data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if not isinstance(e, asyncio.CancelledError):
                    logger.error("Redis listener error: %s", e)
                    await asyncio.sleep(1)

    async def _broadcast_local(self, message: dict):
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.active_connections.remove(conn)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if self.redis:
            try:
                await self.redis.publish(
                    "energygrid:broadcast", json.dumps(message)
                )
                return
            except Exception as e:
                logger.error("Redis publish error, falling back to local: %s", e)
        await self._broadcast_local(message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
