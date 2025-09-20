import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket
import redis.asyncio as redis
from src.core import config


class WebSocketManager:
    def __init__(self):
        # Active connections by user/session
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis_client: redis.Redis = None

    async def initialize(self):
        """Initialize Redis connection for pub/sub using settings from config."""
        self.redis_client = await redis.from_url(
            config.REDIS_URL, decode_responses=True
        )
        logging.info(f"WebSocketManager initialized with Redis at {config.REDIS_URL}")

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and add to active connections"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logging.info(f"WebSocket connected for user: {user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logging.info(f"WebSocket disconnected for user: {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user's connections"""
        if user_id in self.active_connections:
            disconnected_sockets = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected_sockets.add(websocket)

            # Clean up any connections that failed during send
            for ws in disconnected_sockets:
                await self.disconnect(ws, user_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        # Create a copy of keys to avoid issues with modifying dict during iteration
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    async def subscribe_to_updates(self):
        """Subscribe to Redis pub/sub for real-time updates"""
        if not self.redis_client:
            logging.error("Redis client not initialized. Call initialize() first.")
            return

        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("job_updates", "alert_notifications")
        logging.info("Subscribed to 'job_updates' and 'alert_notifications' channels.")

        while True:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast(data)
                    except (json.JSONDecodeError, TypeError) as e:
                        logging.error(f"Error processing pub/sub message data: {e}")
                await asyncio.sleep(0.01)
            except Exception as e:
                logging.error(f"Error in pub/sub subscription loop: {e}")
                # Re-subscribe on error
                await asyncio.sleep(5)
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe("job_updates", "alert_notifications")


# Global WebSocket manager instance
ws_manager = WebSocketManager()
