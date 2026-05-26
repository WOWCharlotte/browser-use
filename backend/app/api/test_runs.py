"""
API routes for Test Run execution, results, and real-time log streaming.
"""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import Config
from app.db.database import get_db
from app.models.test_run import OverrideRequest, TestRunCreate, TestResultView, TestRunView
from app.services.test_execution_service import test_execution_service
from app.utils import uuid7str

logger = logging.getLogger(__name__)

router = APIRouter()


def _error(code: str, message: str, status_code: int = 400) -> JSONResponse:
	return JSONResponse(
		status_code=status_code,
		content={"success": False, "error": message, "code": code},
	)


# ── Test Runs ─────────────────────────────────────────────────────────────────


@router.post("/test-runs")
async def start_test_run(data: TestRunCreate):
	"""Start a new test run."""
	try:
		# Verify plan exists and is confirmed
		db = await get_db()
		try:
			async with db.execute(
				"SELECT status FROM test_plans WHERE id=?", (data.plan_id,)
			) as cursor:
				row = await cursor.fetchone()
				if not row:
					return _error("NOT_FOUND", f"Plan {data.plan_id} not found", 404)
				if row[0] != "confirmed":
					return _error("INVALID_STATE", "Plan must be confirmed before execution")
		finally:
			await db.close()

		# Create a no-op event handler for standalone API calls
		# (agui.py will pass its own on_event when triggered via chat)
		events: list[dict] = []

		async def on_event(event: dict) -> None:
			events.append(event)

		run_id = await test_execution_service.start_run(
			plan_id=data.plan_id,
			max_concurrency=data.max_concurrency,
			on_event=on_event,
			case_ids=data.case_ids,
			rerun_failed=data.rerun_failed,
			max_retries=data.max_retries,
			case_timeout_seconds=data.case_timeout_seconds,
		)
		return {"success": True, "data": {"run_id": run_id}}
	except AssertionError as e:
		return _error("VALIDATION_ERROR", str(e))
	except Exception as e:
		logger.exception("Error starting test run")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.get("/test-runs/{run_id}")
async def get_test_run(run_id: str):
	"""Get test run status."""
	db = await get_db()
	try:
		async with db.execute("SELECT * FROM test_runs WHERE id=?", (run_id,)) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Run {run_id} not found", 404)
			columns = [d[0] for d in cursor.description]
			data = dict(zip(columns, row))
		return {"success": True, "data": data}
	finally:
		await db.close()


@router.post("/test-runs/{run_id}/abort")
async def abort_test_run(run_id: str):
	"""Abort a running test run."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT status FROM test_runs WHERE id=?", (run_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Run {run_id} not found", 404)
			if row[0] != "running":
				return _error("INVALID_STATE", f"Run is {row[0]}, cannot abort")
	finally:
		await db.close()

	await test_execution_service.abort_run(run_id)
	return {"success": True, "data": {"status": "aborted"}}


@router.get("/test-runs/{run_id}/results")
async def get_test_run_results(run_id: str):
	"""Get all results for a test run."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT * FROM test_results WHERE run_id=? ORDER BY started_at", (run_id,)
		) as cursor:
			rows = await cursor.fetchall()
			columns = [d[0] for d in cursor.description]
			results = [dict(zip(columns, row)) for row in rows]
		return {"success": True, "data": results}
	finally:
		await db.close()


# ── Test Results ──────────────────────────────────────────────────────────────


@router.get("/test-results/{result_id}/screenshot")
async def get_result_screenshot(result_id: str):
	"""Get the current browser screenshot for a running/paused test case."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT status FROM test_results WHERE id=?", (result_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Result {result_id} not found", 404)
			if row[0] not in ("running", "paused"):
				return _error("INVALID_STATE", "Case is not currently running")
	finally:
		await db.close()

	# Browser session may not be ready yet — retry briefly
	screenshot = None
	for _ in range(5):
		screenshot = await test_execution_service.take_screenshot(result_id)
		if screenshot is not None:
			break
		await asyncio.sleep(1)

	if screenshot is None:
		return _error("UNAVAILABLE", "Screenshot not available (browser may not be ready)")
	return {"success": True, "data": {"screenshot": screenshot}}


@router.get("/test-results/{result_id}/screenshots")
async def get_result_step_screenshots(result_id: str):
	"""Get all step screenshots for a test result (persisted after completion, or live if running)."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT id FROM test_results WHERE id=?", (result_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Result {result_id} not found", 404)
	finally:
		await db.close()

	try:
		screenshots = await test_execution_service.get_step_screenshots(result_id)
	except Exception as e:
		return _error("INTERNAL", f"Failed to load screenshots: {e}", 500)
	return {"success": True, "data": {"screenshots": screenshots, "total": len(screenshots)}}


@router.put("/test-results/{result_id}/override")
async def override_result(result_id: str, data: OverrideRequest):
	"""Manually override a test result evaluation."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT status FROM test_results WHERE id=?", (result_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Result {result_id} not found", 404)

		current_status = row[0]
		await db.execute(
			"UPDATE test_results SET original_status=?, status=?, override_reason=? WHERE id=?",
			(current_status, data.status, data.reason, result_id),
		)
		await db.commit()
		return {"success": True, "data": {"status": data.status, "original_status": current_status}}
	finally:
		await db.close()


@router.get("/test-results/{result_id}/logs")
async def get_result_logs(result_id: str, tail: int = Query(default=0, ge=0)):
	"""Get execution logs for a test result."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT run_id, case_id FROM test_results WHERE id=?", (result_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Result {result_id} not found", 404)
			run_id, case_id = row[0], row[1]
	finally:
		await db.close()

	# Find log file
	log_dir = Config.TRAJECTORY_DIR / run_id
	log_files = list(log_dir.glob(f"{case_id}_*.log")) if log_dir.exists() else []
	if not log_files:
		return _error("NOT_FOUND", "Log file not found", 404)

	log_path = log_files[0]
	try:
		content = log_path.read_text(encoding="utf-8")
	except FileNotFoundError:
		return _error("NOT_FOUND", "Log file not found", 404)

	lines = content.splitlines()
	if tail > 0:
		lines = lines[-tail:]

	return {"success": True, "data": {"lines": lines, "total": len(content.splitlines())}}


@router.get("/test-results/{result_id}/logs/stream")
async def stream_result_logs(result_id: str):
	"""SSE endpoint for real-time log streaming."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT run_id, case_id, status FROM test_results WHERE id=?", (result_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Result {result_id} not found", 404)
			run_id, case_id, status = row[0], row[1], row[2]
	finally:
		await db.close()

	if status == "pending":
		return _error("INVALID_STATE", "Case has not started yet")

	# Find log file
	log_dir = Config.TRAJECTORY_DIR / run_id
	log_files = list(log_dir.glob(f"{case_id}_*.log")) if log_dir.exists() else []

	# If case is running but log file not yet created, wait briefly
	if not log_files and status in ("running", "paused"):
		for _ in range(10):  # wait up to 5s
			await asyncio.sleep(0.5)
			log_files = list(log_dir.glob(f"{case_id}_*.log")) if log_dir.exists() else []
			if log_files:
				break

	if not log_files:
		return _error("NOT_FOUND", "Log file not found", 404)

	log_path = log_files[0]

	async def event_generator():
		try:
			# Read existing content
			if log_path.exists():
				content = log_path.read_text(encoding="utf-8")
				if content:
					yield f"event: log\ndata: {json.dumps(content, ensure_ascii=False)}\n\n"

			last_pos = log_path.stat().st_size if log_path.exists() else 0

			# Tail new content while case is running/paused
			while True:
				# Check if case is still active
				db_check = await get_db()
				try:
					async with db_check.execute(
						"SELECT status FROM test_results WHERE id=?", (result_id,)
					) as cursor:
						row = await cursor.fetchone()
						if not row or row[0] not in ("running", "paused"):
							# Send any remaining content before closing
							if log_path.exists():
								current_size = log_path.stat().st_size
								if current_size > last_pos:
									with open(str(log_path), "r", encoding="utf-8") as f:
										f.seek(last_pos)
										new_content = f.read()
									if new_content:
										yield f"event: log\ndata: {json.dumps(new_content, ensure_ascii=False)}\n\n"
							yield "event: done\ndata: \n\n"
							return
				finally:
					await db_check.close()

				# Read new content
				if log_path.exists():
					current_size = log_path.stat().st_size
					if current_size > last_pos:
						with open(str(log_path), "r", encoding="utf-8") as f:
							f.seek(last_pos)
							new_content = f.read()
						last_pos = current_size
						if new_content:
							yield f"event: log\ndata: {json.dumps(new_content, ensure_ascii=False)}\n\n"

				await asyncio.sleep(0.3)
		except Exception as e:
			yield f"event: error\ndata: {json.dumps(str(e))}\n\n"

	return StreamingResponse(
		event_generator(),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"Connection": "keep-alive",
			"X-Accel-Buffering": "no",
		},
	)


@router.post("/test-results/{result_id}/retry")
async def retry_result(result_id: str):
	"""Retry a single failed/error test result."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT status FROM test_results WHERE id=?", (result_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return _error("NOT_FOUND", f"Result {result_id} not found", 404)
			if row[0] not in ("failed", "error"):
				return _error("INVALID_STATE", f"Can only retry failed/error results, got {row[0]}")
	finally:
		await db.close()

	try:
		status = await test_execution_service.retry_result(result_id)
		return {"success": True, "data": {"status": status}}
	except ValueError as e:
		return _error("NOT_FOUND", str(e), 404)
	except Exception as e:
		logger.exception("Error retrying result")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.post("/test-results/{result_id}/pause")
async def pause_result(result_id: str):
	"""Pause a running test case at the next step boundary."""
	ok = await test_execution_service.pause_result(result_id)
	if not ok:
		return _error("INVALID_STATE", "Case is not running or already paused")
	return {"success": True, "data": {"paused": True}}


@router.post("/test-results/{result_id}/resume")
async def resume_result(result_id: str):
	"""Resume a paused test case."""
	ok = await test_execution_service.resume_result(result_id)
	if not ok:
		return _error("INVALID_STATE", "Case is not paused")
	return {"success": True, "data": {"paused": False}}


@router.post("/test-results/{result_id}/stop")
async def stop_result(result_id: str):
	"""Stop a running or paused test case immediately."""
	ok = await test_execution_service.stop_result(result_id)
	if not ok:
		return _error("INVALID_STATE", "Case is not running")
	return {"success": True, "data": {"stopped": True}}
