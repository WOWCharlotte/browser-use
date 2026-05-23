"""
Test Case Ingestion API Endpoints.

Provides endpoints for parsing test cases from Excel/Markdown documents.
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.ingestion import IngestionResponse
from app.services.ingestion_service import ingestion_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingestion/upload")
async def ingest_test_case(
	file: UploadFile | None = File(None, description="Test case file (.xlsx, .xls, .md, .markdown)"),
	markdown_content: str | None = Form(None, description="Raw markdown content (alternative to file upload)"),
) -> IngestionResponse:
	"""
	Parse a test case from file or markdown content.

	Accepts either:
	- File upload: Excel (.xlsx, .xls) or Markdown (.md, .markdown)
	- Markdown content: Raw markdown text (e.g., from Notion/语雀 copy-paste)

	File size limit: 5MB.
	"""
	try:
		if file is not None:
			logger.info(f"Received file upload: {file.filename}")
			content = await file.read()
			test_case = await ingestion_service.ingest_file(file.filename, content)
			logger.info(f"Successfully processed file: {file.filename}")
			return IngestionResponse(
				success=True,
				case_name=test_case.case_name,
				start_url=test_case.start_url,
				steps=test_case.steps,
				global_variables=test_case.global_variables,
			)
		elif markdown_content is not None:
			logger.info("Received markdown content submission")
			test_case = await ingestion_service.ingest_markdown(markdown_content)
			logger.info("Successfully processed markdown content")
			return IngestionResponse(
				success=True,
				case_name=test_case.case_name,
				start_url=test_case.start_url,
				steps=test_case.steps,
				global_variables=test_case.global_variables,
				raw_markdown=markdown_content,
			)
		else:
			raise HTTPException(status_code=400, detail="Either file or markdown_content must be provided")

	except ValueError as e:
		logger.warning(f"Validation error: {e}")
		raise HTTPException(status_code=400, detail=str(e))
	except Exception as e:
		logger.error(f"Ingestion failed: {e}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")