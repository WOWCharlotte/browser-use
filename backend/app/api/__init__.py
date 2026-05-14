from fastapi import APIRouter

from app.api.browser import router as browser_router
from app.api.chat import router as chat_router
from app.api.agent import router as agent_router
from app.api.sessions import router as sessions_router
from app.api.agui import router as agui_router

router = APIRouter()