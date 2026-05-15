from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.sessions import router as sessions_router
from app.api.agui import router as agui_router

router = APIRouter()