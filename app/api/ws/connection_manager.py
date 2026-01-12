from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):

        self.active_connections: Dict[str, List[WebSocket]] = {}

