import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.monitoring.websocket import ws_manager

router = APIRouter()

@router.websocket("/ws/monitoring/{user_id}")
async def websocket_monitoring_endpoint(websocket: WebSocket, user_id: str):
    """
    Handles the WebSocket connection for a given user to stream real-time monitoring data.
    """
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            # The server will primarily push data. This loop listens for client messages.
            # This can be used for features like filtering or pausing the stream.
            data = await websocket.receive_text()
            logging.debug(f"Received message from {user_id}: {data}")
            # Example of handling a client message:
            # try:
            #     message = json.loads(data)
            #     if message.get("action") == "ping":
            #         await websocket.send_json({"response": "pong"})
            # except json.JSONDecodeError:
            #     logging.warning(f"Received non-JSON message from {user_id}")

    except WebSocketDisconnect:
        logging.info(f"Client {user_id} disconnected.")
        await ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logging.error(f"An error occurred in the WebSocket connection for {user_id}: {e}", exc_info=True)
        await ws_manager.disconnect(websocket, user_id)
