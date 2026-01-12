from fastapi import APIRouter
from starlette.websockets import WebSocket

from app.api.ws.connection_manager import ConnectionManager

manager = ConnectionManager()

router = APIRouter()

@router.websocket("/ws/{conversation_id}")
async def ws_chat(websocket: WebSocket, conversation_id: int):
    await manager.connect(conversation_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(conversation_id, data)
    finally:
        manager.disconnect(conversation_id, websocket)