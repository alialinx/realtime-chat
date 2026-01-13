# app/main.py
from fastapi import FastAPI, APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBasic
from starlette.middleware.cors import CORSMiddleware

from app.api import auth, friends, conversations, messages
from app.api.ws import ws

app = FastAPI(
    title="Realtime - Chat",
    description="Realtime - Chat API",
    version="1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    contact={"name": "Ali A.", "email": "alialinxz@gmail.com"},
)

security = HTTPBasic()


# Swagger ana sayfa
@app.get("/", include_in_schema=False)
async def homepage():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Realtime - Chat",
    )


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router
router = APIRouter()

app.include_router(auth.router)
app.include_router(friends.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(ws.router)
