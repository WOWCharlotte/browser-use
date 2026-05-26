"""
Reports API — HTML, PDF, and Excel report generation endpoints.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.db.database import get_db
from app.services.report_service import report_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _error(code: str, message: str, status_code: int = 400) -> JSONResponse:
	return JSONResponse(
		status_code=status_code,
		content={"success": False, "error": message, "code": code},
	)


async def _validate_run_completed(run_id: str) -> str | None:
	"""Validate run exists and is completed. Returns error message or None."""
	db = await get_db()
	try:
		async with db.execute(
			"SELECT status FROM test_runs WHERE id=?", (run_id,)
		) as cursor:
			row = await cursor.fetchone()
			if not row:
				return "NOT_FOUND"
			if row[0] not in ("completed", "aborted"):
				return "NOT_COMPLETED"
	finally:
		await db.close()
	return None


@router.get("/test-runs/{run_id}/report")
async def get_html_report(run_id: str):
	"""Get HTML test report for a completed run."""
	err = await _validate_run_completed(run_id)
	if err == "NOT_FOUND":
		return _error("NOT_FOUND", f"Run {run_id} not found", 404)
	if err == "NOT_COMPLETED":
		return _error("INVALID_STATE", "Run has not completed yet")

	try:
		report_path = await report_service.generate_html(run_id)
		html_content = report_path.read_text(encoding="utf-8")
		return HTMLResponse(content=html_content)
	except Exception as e:
		logger.error(f"Failed to generate HTML report for {run_id}: {e}")
		return _error("INTERNAL", f"Report generation failed: {e}", 500)


@router.get("/test-runs/{run_id}/report/pdf")
async def get_pdf_report(run_id: str):
	"""Download PDF test report for a completed run."""
	err = await _validate_run_completed(run_id)
	if err == "NOT_FOUND":
		return _error("NOT_FOUND", f"Run {run_id} not found", 404)
	if err == "NOT_COMPLETED":
		return _error("INVALID_STATE", "Run has not completed yet")

	try:
		pdf_path = await report_service.generate_pdf(run_id)
		return FileResponse(
			path=str(pdf_path),
			media_type="application/pdf",
			filename=f"test-report-{run_id[:8]}.pdf",
		)
	except Exception as e:
		logger.error(f"Failed to generate PDF report for {run_id}: {e}")
		return _error("INTERNAL", f"PDF generation failed: {e}", 500)


@router.get("/test-runs/{run_id}/report/excel")
async def get_excel_report(run_id: str):
	"""Download Excel test report for a completed run."""
	err = await _validate_run_completed(run_id)
	if err == "NOT_FOUND":
		return _error("NOT_FOUND", f"Run {run_id} not found", 404)
	if err == "NOT_COMPLETED":
		return _error("INVALID_STATE", "Run has not completed yet")

	try:
		excel_path = await report_service.generate_excel(run_id)
		return FileResponse(
			path=str(excel_path),
			media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			filename=f"test-report-{run_id[:8]}.xlsx",
		)
	except Exception as e:
		logger.error(f"Failed to generate Excel report for {run_id}: {e}")
		return _error("INTERNAL", f"Excel generation failed: {e}", 500)
