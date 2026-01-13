from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):

        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        self.ws_user: Dict[WebSocket, int] = {}

    async def connect(self, conversation_id, websocket: WebSocket, user_id):
        await websocket.accept()

        self.active_connections.setdefault(conversation_id, set()).add(websocket)
        self.user_connections.setdefault(user_id, set()).add(websocket)
        self.ws_user[websocket] = user_id

    async def broadcast(self, conversation_id, message):

        if conversation_id not in self.active_connections:
            return

        dead: set[WebSocket] = set()

        for websocket in list(self.active_connections[conversation_id]):

            try:

                await websocket.send_json(message)
            except Exception:
                dead.add(websocket)

        for ws in dead:
            self.active_connections[conversation_id].discard(ws)

            uid = self.ws_user.get(ws)
            if uid is not None and uid not in self.user_connections:
                self.user_connections[uid].discard(ws)
                if len(self.user_connections[uid]) == 0:
                    del self.user_connections[uid]

            self.ws_user.pop(ws, None)

        if len(self.active_connections[conversation_id]) == 0:
            del self.active_connections[conversation_id]

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0

    def disconnect(self, conversation_id, websocket: WebSocket):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)

            self.active_connections[conversation_id].discard(websocket)
            if len(self.active_connections[conversation_id]) == 0:
                del self.active_connections[conversation_id]

        uid = self.ws_user.get(websocket)

        if uid is not None and uid in self.user_connections:
            self.user_connections[uid].discard(websocket)
            if len(self.user_connections[uid]) == 0:
                del self.user_connections[uid]

        self.ws_user.pop(websocket, None)
