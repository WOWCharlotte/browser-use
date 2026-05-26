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

	# Check browser availability
	from app.config import Config
	from browser_use.browser.watchdogs.local_browser_watchdog import LocalBrowserWatchdog
	chrome_path = Config.CHROME_EXECUTABLE_PATH
	if chrome_path:
		from pathlib import Path
		if Path(chrome_path).is_file():
			logger.info(f"Browser check passed: using configured executable at {chrome_path}")
		else:
			logger.error(f"Browser check failed: CHROME_EXECUTABLE_PATH={chrome_path!r} does not exist")
			raise RuntimeError(f"Configured browser executable not found: {chrome_path}")
	else:
		found = LocalBrowserWatchdog._find_installed_browser_path()
		if found:
			logger.info(f"Browser check passed: auto-detected browser at {found}")
		else:
			logger.error(
				"Browser check failed: no Chrome/Chromium found. "
				"Set CHROME_EXECUTABLE_PATH in backend/.env or run `uvx playwright install chromium`."
			)
			raise RuntimeError("No Chrome/Chromium browser found, cannot start server.")

	# Recover residual running states from previous crashes
	from app.services.test_execution_service import test_execution_service
	try:
		await test_execution_service.recover_on_startup()
		await test_execution_service.cleanup_old_trajectories()
	except Exception as e:
		logger.warning(f"Startup recovery warning: {e}")


# Import routers after app creation to avoid circular imports
from app.api import agui, reports, sessions, test_plans, test_replays, test_runs

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(agui.router, prefix="/api", tags=["agui"])
app.include_router(test_plans.router, prefix="/api", tags=["test-plans"])
app.include_router(test_runs.router, prefix="/api", tags=["test-runs"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(test_replays.router, prefix="/api", tags=["test-replays"])