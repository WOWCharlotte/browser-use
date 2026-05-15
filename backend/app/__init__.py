import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Workspace Backend")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
	from app.db.database import init_db

	try:
		await init_db()
	except Exception as e:
		logger.error(f"Failed to initialize database: {e}")
		raise


# Import routers after app creation to avoid circular imports
from app.api import sessions,agent, agui

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(agent.router, prefix="/api", tags=["agent"])
app.include_router(agui.router, prefix="/api", tags=["agui"])