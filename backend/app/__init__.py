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

	# Recover residual running states from previous crashes
	from app.services.test_execution_service import test_execution_service
	try:
		await test_execution_service.recover_on_startup()
		await test_execution_service.cleanup_old_trajectories()
	except Exception as e:
		logger.warning(f"Startup recovery warning: {e}")


# Import routers after app creation to avoid circular imports
from app.api import agui, sessions, test_plans, test_runs

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(agui.router, prefix="/api", tags=["agui"])
app.include_router(test_plans.router, prefix="/api", tags=["test-plans"])
app.include_router(test_runs.router, prefix="/api", tags=["test-runs"])