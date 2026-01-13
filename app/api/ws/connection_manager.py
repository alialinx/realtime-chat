from typing import Dict, List, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):

        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.ws_user: Dict[WebSocket, int] = {}
        print(f"Connection manager initialized: {self.active_connections}", flush=True, )

    async def connect(self, conversation_id, websocket: WebSocket, user_id):
        await websocket.accept()

        self.active_connections.setdefault(conversation_id, set()).add(websocket)
        self.ws_user[websocket] = user_id
        print(f"Connection accepted active_connections: {self.active_connections}", flush=True, )



    async def broadcast(self, conversation_id, message):

        if conversation_id not in self.active_connections:
            return

        dead: set[WebSocket] = set()

        for websocket in self.active_connections[conversation_id]:
            print(f"Broadcasting message: {message}", flush=True, )

            try:

                await websocket.send_json(message)
                print("Message sent", flush=True, )
            except Exception:
                dead.add(websocket)

        for ws in dead:
            self.active_connections[conversation_id].discard(ws)

        if len(self.active_connections[conversation_id]) == 0:
            del self.active_connections[conversation_id]


    def disconnect(self, conversation_id, websocket: WebSocket):
        if conversation_id in self.active_connections:
            print(f"Disconnecting connection: {conversation_id}", flush=True, )
            self.active_connections[conversation_id].discard(websocket)

            if len(self.active_connections[conversation_id]) == 0:
                del self.active_connections[conversation_id]

        self.ws_user.pop(websocket, None)
