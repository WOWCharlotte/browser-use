import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import BackendSettings
from app.logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)


async def initialize_backend() -> None:
	"""Run backend startup checks and recovery tasks."""
	from app.config import Config
	from app.db.database import init_db
	from app.services.model_router import warm_up_model_router
	from app.services.test_execution_service import test_execution_service
	from browser_use.browser.watchdogs.local_browser_watchdog import LocalBrowserWatchdog

	try:
		await init_db()
	except Exception as exc:
		logger.error("Failed to initialize database: %s", exc)
		raise

	try:
		warm_up_model_router()
	except Exception as exc:
		logger.error("Failed to warm up model router: %s", exc)
		raise

	chrome_path = Config.CHROME_EXECUTABLE_PATH
	if chrome_path:
		if Path(chrome_path).is_file():
			logger.info("Browser check passed: using configured executable at %s", chrome_path)
		else:
			logger.error("Browser check failed: CHROME_EXECUTABLE_PATH=%r does not exist", chrome_path)
			raise RuntimeError(f"Configured browser executable not found: {chrome_path}")
	else:
		found = LocalBrowserWatchdog._find_installed_browser_path()
		if found:
			logger.info("Browser check passed: auto-detected browser at %s", found)
		else:
			logger.error(
				"Browser check failed: no Chrome/Chromium found. "
				"Set CHROME_EXECUTABLE_PATH in backend/.env or run `uvx playwright install chromium`."
			)
			raise RuntimeError("No Chrome/Chromium browser found, cannot start server.")

	try:
		await test_execution_service.recover_on_startup()
		await test_execution_service.cleanup_old_trajectories()
	except Exception as exc:
		logger.warning("Startup recovery warning: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
	"""FastAPI lifespan hook for backend startup."""
	await initialize_backend()
	yield


def create_app(settings: BackendSettings | None = None) -> FastAPI:
	"""Create and configure the FastAPI backend app."""
	backend_settings = settings or BackendSettings()
	fastapi_app = FastAPI(title="AI Workspace Backend", lifespan=lifespan)
	fastapi_app.state.settings = backend_settings

	fastapi_app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	from app.api import agui, chat, reports, sessions, test_plans, test_replays, test_runs

	fastapi_app.include_router(sessions.router, prefix="/api", tags=["sessions"])
	fastapi_app.include_router(chat.router, prefix="/api", tags=["chat"])
	fastapi_app.include_router(agui.router, prefix="/api", tags=["agui"])
	fastapi_app.include_router(test_plans.router, prefix="/api", tags=["test-plans"])
	fastapi_app.include_router(test_runs.router, prefix="/api", tags=["test-runs"])
	fastapi_app.include_router(reports.router, prefix="/api", tags=["reports"])
	fastapi_app.include_router(test_replays.router, prefix="/api", tags=["test-replays"])

	return fastapi_app


app = create_app()
