from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.api.functions import get_user_id_from_token, check_conversation, messages_insert_to_db, set_user_online, touch_last_seen, get_recipient_id, mark_delivered, mark_conversation_read
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

    check_conver, _ = check_conversation(conversation_id, user_id)

    if not check_conver:
        await websocket.close(code=1008)

        return

    await manager.connect(conversation_id, websocket, user_id)
    set_user_online(user_id, True)


    try:

        while True:

            data = await websocket.receive_json()

            event_type = data.get("type")

            if event_type == "message.send":
                body = data.get("body")
                if not body:
                    continue

                msg = messages_insert_to_db(conversation_id, user_id, body)

                recipient_id = get_recipient_id(conversation_id, user_id)
                if recipient_id is not None and manager.is_user_online(recipient_id):
                    delivered_msg = mark_delivered(msg["id"])
                    if delivered_msg:
                        msg = delivered_msg

                await manager.broadcast(conversation_id, {"type": "message.new","data": msg})


            elif event_type == "conversation.read":
                last_id = data.get("last_message_id")
                if not last_id:
                    continue

                updated = mark_conversation_read(conversation_id, user_id, int(last_id))

                await manager.broadcast(conversation_id, {
                    "type": "conversation.read",
                    "data": {
                        "conversation_id": conversation_id,
                        "reader_id": user_id,
                        "last_message_id": int(last_id),
                        "updated_count": updated
                    }
                })

            elif event_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass

    finally:
        manager.disconnect(conversation_id,websocket)
        set_user_online(user_id, False)