"""
Test Case Ingestion API Endpoints.

Provides endpoints for parsing test cases from Excel/Markdown documents.
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.ingestion import PlanIngestionResponse
from app.services.ingestion_service import ingestion_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingestion/upload")
async def ingest_test_plan(
	file: UploadFile | None = File(None, description="Test case file (.xlsx, .xls, .md, .markdown)"),
	markdown_content: str | None = Form(None, description="Raw markdown content (alternative to file upload)"),
) -> PlanIngestionResponse:
	"""
	Parse a test plan from file or markdown content.

	Returns all test cases extracted from the document, with steps, variables,
	and merged variable sets for parameterized cases.

	Accepts either:
	- File upload: Excel (.xlsx, .xls) or Markdown (.md, .markdown)
	- Markdown content: Raw markdown text

	File size limit: 5MB.
	"""
	try:
		if file is not None:
			logger.info(f"Received file upload: {file.filename}")
			content = await file.read()
			plan = await ingestion_service.ingest_file(file.filename, content)
			logger.info(f"Parsed {len(plan.test_cases)} cases from file: {file.filename}")
			return PlanIngestionResponse(
				success=True,
				test_cases=plan.test_cases,
				total_cases=len(plan.test_cases),
			)
		elif markdown_content is not None:
			logger.info("Received markdown content submission")
			plan = await ingestion_service.ingest_markdown(markdown_content)
			logger.info(f"Parsed {len(plan.test_cases)} cases from markdown")
			return PlanIngestionResponse(
				success=True,
				test_cases=plan.test_cases,
				total_cases=len(plan.test_cases),
				raw_markdown=markdown_content,
			)
		else:
			raise HTTPException(status_code=400, detail="Either file or markdown_content must be provided")

	except ValueError as e:
		logger.warning(f"Validation error: {e}")
		raise HTTPException(status_code=400, detail=str(e))
	except Exception as e:
		logger.error(f"Ingestion failed: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail="Ingestion failed")