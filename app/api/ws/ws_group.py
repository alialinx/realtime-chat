import psycopg2
from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.api.functions import get_user_id_from_token, check_groups, set_user_online, group_messages_insert_to_db, mark_group_read
from app.api.ws.connection_manager import ConnectionManager

group_manager = ConnectionManager()

router = APIRouter()


@router.websocket('/ws/groups/{group_id}')
async def web_socker(websocket: WebSocket, group_id: int):
    token = websocket.query_params.get('token')

    print("token", token)

    if not token:
        await websocket.close(code=1008)
        return

    user_id = get_user_id_from_token(token)
    print("user_id", user_id)


    if not user_id:
        await websocket.close(code=1008)
        return

    check_group, _ = check_groups(group_id, user_id)
    print("WS check_group:", check_group, "extra:", _)
    if not check_group:
        await websocket.close(code=1008)
        return

    await group_manager.connect(group_id, websocket, user_id)
    set_user_online(user_id, True)

    try:

        while True:

            data = await websocket.receive_json()
            event_type = data.get('type')

            if event_type == "group.message.sent":

                body = (data.get("body") or "").strip()
                if not body:
                    continue

                msg = group_messages_insert_to_db(group_id, user_id, body)

                await group_manager.broadcast(group_id, {"type": "group.message.new", "data": msg}, )


            elif event_type == "group.read":
                mark_group_read(group_id, user_id)
                await websocket.send_json({"type": "group.read.ok", "group_id": group_id})

            elif event_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass

    finally:
        group_manager.disconnect(group_id, websocket)
        if not group_manager.is_user_online(user_id):
            set_user_online(user_id, False)