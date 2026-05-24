"""
API routes for Test Plan and Test Case management.
"""

import logging

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.models.test_plan import (
	TestCaseCreate,
	TestCaseUpdate,
	TestPlanCreate,
	TestPlanUpdate,
	VariableImportRequest,
)
from app.services.test_plan_service import test_plan_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _error(code: str, message: str, status_code: int = 400) -> JSONResponse:
	return JSONResponse(
		status_code=status_code,
		content={"success": False, "error": message, "code": code},
	)


# ── Test Plans ──────────────────────────────────────────────────────────────

@router.post("/test-plans/upload")
async def upload_test_plan(
	file: UploadFile = File(...),
	name: str = Form(...),
	max_concurrency: int = Form(default=3),
):
	"""Upload a file (Excel/Markdown), parse all test cases, and create a test plan."""
	from app.services.ingestion_service import ingestion_service

	try:
		file_content = await file.read()
		parsed_plan = await ingestion_service.ingest_file(file.filename or "upload", file_content)

		detail = await test_plan_service.import_parsed_plan(
			parsed=parsed_plan,
			name=name,
			source_file_name=file.filename,
			max_concurrency=max_concurrency,
		)
		return {"success": True, "data": detail.model_dump()}
	except ValueError as e:
		return _error("PARSE_ERROR", str(e))
	except Exception as e:
		logger.exception("Unexpected error during file upload")
		return _error("INTERNAL_ERROR", "An internal error occurred", 500)


@router.post("/test-plans/manual")
async def create_test_plan(data: TestPlanCreate):
	"""Manually create a test plan."""
	try:
		plan = await test_plan_service.create_plan(data)
		return {"success": True, "data": plan.model_dump()}
	except Exception as e:
		logger.exception("Error creating test plan")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.get("/test-plans")
async def list_test_plans():
	"""List all test plans."""
	plans = await test_plan_service.list_plans()
	return {"success": True, "data": [p.model_dump() for p in plans]}


@router.get("/test-plans/{plan_id}")
async def get_test_plan(plan_id: str):
	"""Get a test plan with all its cases."""
	detail = await test_plan_service.get_plan_detail(plan_id)
	if detail is None:
		return _error("NOT_FOUND", f"Test plan not found: {plan_id}", 404)
	return {"success": True, "data": detail.model_dump()}


@router.put("/test-plans/{plan_id}")
async def update_test_plan(plan_id: str, data: TestPlanUpdate):
	"""Update a test plan."""
	try:
		plan = await test_plan_service.update_plan(plan_id, data)
		return {"success": True, "data": plan.model_dump()}
	except ValueError as e:
		return _error("NOT_FOUND", str(e), 404)
	except Exception as e:
		logger.exception("Error updating test plan")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.delete("/test-plans/{plan_id}")
async def delete_test_plan(plan_id: str):
	"""Delete a test plan and all its cases."""
	deleted = await test_plan_service.delete_plan(plan_id)
	if not deleted:
		return _error("NOT_FOUND", f"Test plan not found: {plan_id}", 404)
	return {"success": True}


@router.put("/test-plans/{plan_id}/confirm")
async def confirm_test_plan(plan_id: str):
	"""Confirm a test plan (draft → confirmed)."""
	try:
		plan = await test_plan_service.confirm_plan(plan_id)
		return {"success": True, "data": plan.model_dump()}
	except ValueError as e:
		msg = str(e)
		if "not found" in msg:
			return _error("NOT_FOUND", msg, 404)
		return _error("INVALID_STATUS", msg, 400)
	except Exception as e:
		logger.exception("Error confirming test plan")
		return _error("INTERNAL_ERROR", str(e), 500)


# ── Test Cases ──────────────────────────────────────────────────────────────

@router.post("/test-plans/{plan_id}/cases")
async def create_test_case(plan_id: str, data: TestCaseCreate):
	"""Add a test case to a plan."""
	try:
		case = await test_plan_service.create_case(plan_id, data)
		return {"success": True, "data": case.model_dump()}
	except ValueError as e:
		return _error("NOT_FOUND", str(e), 404)
	except Exception as e:
		logger.exception("Error creating test case")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.put("/test-cases/{case_id}")
async def update_test_case(case_id: str, data: TestCaseUpdate):
	"""Edit a test case."""
	try:
		case = await test_plan_service.update_case(case_id, data)
		return {"success": True, "data": case.model_dump()}
	except ValueError as e:
		return _error("NOT_FOUND", str(e), 404)
	except Exception as e:
		logger.exception("Error updating test case")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.delete("/test-cases/{case_id}")
async def delete_test_case(case_id: str):
	"""Delete a test case."""
	deleted = await test_plan_service.delete_case(case_id)
	if not deleted:
		return _error("NOT_FOUND", f"Test case not found: {case_id}", 404)
	return {"success": True}


@router.post("/test-cases/{case_id}/variables/import")
async def import_variable_sets(case_id: str, data: VariableImportRequest):
	"""Import variable sets for a test case."""
	try:
		sets = await test_plan_service.create_variable_sets(case_id, data.variable_sets)
		return {"success": True, "data": [s.model_dump() for s in sets]}
	except ValueError as e:
		return _error("NOT_FOUND", str(e), 404)
	except Exception as e:
		logger.exception("Error importing variable sets")
		return _error("INTERNAL_ERROR", str(e), 500)


@router.get("/test-cases/{case_id}/variables")
async def get_variable_sets(case_id: str):
	"""Get all variable sets for a test case."""
	sets = await test_plan_service.get_variable_sets(case_id)
	return {"success": True, "data": [s.model_dump() for s in sets]}
