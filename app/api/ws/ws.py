from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.api.functions import get_user_id_from_token, check_conversation, messages_insert_to_db
from app.api.ws.connection_manager import ConnectionManager


manager = ConnectionManager()

router = APIRouter()




@router.websocket("/ws/conversations/{conversation_id}")
async def ws_chat(websocket: WebSocket, conversation_id: int):

    token = websocket.query_params.get("token")

    user_id = get_user_id_from_token(token)

    if not token:
        await websocket.close(code=1008)
        return

    check_conver, conversation_message = check_conversation(conversation_id, user_id)

    if not check_conver:
        await websocket.close(code=1008)

        return

    await manager.connect(conversation_id, websocket)

    try:

        while True:

            data = await websocket.receive_json()

            msg = messages_insert_to_db(conversation_id, user_id, data["body"])

            await manager.broadcast(conversation_id, {"type": "message.new", "data": msg})

    except WebSocketDisconnect:
        pass

    finally:
        manager.disconnect(conversation_id,websocket)