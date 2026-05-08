from fastapi import APIRouter

from app.api.browser import router as browser_router
from app.services.session_service import session_service, SessionService

router = APIRouter()