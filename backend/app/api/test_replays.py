"""
API routes for Test Replay management.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.test_replay import ReplayRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _error(code: str, message: str, status_code: int = 400) -> JSONResponse:
	return JSONResponse(
		status_code=status_code,
		content={"success": False, "error": message, "code": code},
	)


@router.post("/test-results/{result_id}/replay")
async def start_replay(result_id: str, data: ReplayRequest):
	"""Start a replay of a test result's trajectory."""
	from app.db.database import get_db
	from app.services.test_replay_service import test_replay_service

	# Verify result exists and has a trajectory
	db = await get_db()
	try:
		async with db.execute(
			"SELECT status, trajectory_path FROM test_results WHERE id=?",
			(result_id,),
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Result {result_id} not found", 404)
			status, trajectory_path = row[0], row[1]
			if status in ("pending", "running"):
				return _error("INVALID_STATE", f"Cannot replay a {status} result")
			if not trajectory_path:
				return _error("NO_TRAJECTORY", "No trajectory saved for this result")
	finally:
		await db.close()

	try:
		replay_id = await test_replay_service.replay(
			result_id=result_id,
			new_variables=data.new_variables,
		)
		return {"success": True, "data": {"replay_id": replay_id}}
	except ValueError as e:
		return _error("VALIDATION_ERROR", str(e))
	except Exception as e:
		logger.exception("Error starting replay")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.get("/test-replays/{replay_id}")
async def get_replay(replay_id: str):
	"""Get replay status."""
	from app.services.test_replay_service import test_replay_service

	replay = await test_replay_service.get_replay(replay_id)
	if not replay:
		return _error("NOT_FOUND", f"Replay {replay_id} not found", 404)
	return {"success": True, "data": replay}
