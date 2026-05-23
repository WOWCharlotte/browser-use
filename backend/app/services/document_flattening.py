"""
Document Flattening Engine for Test Case Ingestion.

Provides unified interface to convert various document formats (Excel, Markdown)
into a standardized Markdown string for LLM processing.
"""

import io
import logging
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger(__name__)


class DocumentFlattener(ABC):
	"""Abstract base class for document flattening."""

	@abstractmethod
	def flatten(self, content: bytes) -> str:
		"""Convert document content to markdown string."""
		...


class ExcelFlattener(DocumentFlattener):
	"""Flattens Excel (.xlsx) files to Markdown using pandas."""

	SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}

	def flatten(self, content: bytes) -> str:
		"""
		Convert Excel content to markdown table.

		Iterates through all worksheets and combines into a single markdown document.
		Each sheet is converted to a markdown table with sheet name as header.
		"""
		try:
			# Read Excel from bytes
			excel_file = io.BytesIO(content)

			# Get all sheet names first
			xl_file = pd.ExcelFile(excel_file, engine="openpyxl")
			sheet_names = xl_file.sheet_names
			logger.debug(f"Excel file contains {len(sheet_names)} sheets: {sheet_names}")

			# Iterate through all sheets and combine
			markdown_parts = []
			for sheet_name in sheet_names:
				# Read each sheet fresh from the original bytes
				df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name, engine="openpyxl")

				# Add sheet name as header
				markdown_parts.append(f"## {sheet_name}\n")

				# Convert to markdown table
				if not df.empty:
					markdown_parts.append(df.to_markdown(index=False))
				else:
					markdown_parts.append("(Empty sheet)")

				markdown_parts.append("\n")

			result = "##".join(markdown_parts)
			logger.debug(f"Excel flattened to markdown, length={len(result)}")
			return result
		except Exception as e:
			logger.error(f"Failed to parse Excel file: {e}")
			raise ValueError(f"Failed to parse Excel file: {e}")


class MarkdownFlattener(DocumentFlattener):
	"""Flattens Markdown (.md) files to text."""

	SUPPORTED_EXTENSIONS = {".md", ".markdown"}

	def flatten(self, content: bytes) -> str:
		"""
		Convert markdown content to string.

		Reads as UTF-8 text without transformation.
		"""
		try:
			return content.decode("utf-8")
		except UnicodeDecodeError as e:
			raise ValueError(f"Failed to decode markdown file: {e}")


class DocumentFlatteningEngine:
	"""
	Unified document flattening engine.

	Routes documents to appropriate flattener based on file extension.
	"""

	SUPPORTED_TYPES = {".xlsx", ".xls", ".md", ".markdown"}

	def __init__(self) -> None:
		self._flattners: dict[str, DocumentFlattener] = {
			".xlsx": ExcelFlattener(),
			".xls": ExcelFlattener(),
			".md": MarkdownFlattener(),
			".markdown": MarkdownFlattener(),
		}

	def is_supported(self, file_name: str) -> bool:
		"""Check if file type is supported."""
		ext = self._get_extension(file_name)
		return ext in self.SUPPORTED_TYPES

	def flatten(self, file_name: str, content: bytes) -> str:
		"""
		Flatten document to markdown.

		Args:
			file_name: Original file name with extension
			content: Raw file bytes

		Returns:
			Flattened markdown string

		Raises:
			ValueError: If file type is not supported
		"""
		ext = self._get_extension(file_name)
		logger.debug(f"Flattening document: {file_name} (ext={ext})")

		if ext not in self.SUPPORTED_TYPES:
			raise ValueError(
				f"Unsupported file type: {ext}. Supported types: {', '.join(sorted(self.SUPPORTED_TYPES))}"
			)

		flattener = self._flattners.get(ext)
		if not flattener:
			raise ValueError(f"No flattener registered for: {ext}")

		result = flattener.flatten(content)
		logger.info(f"Successfully flattened {file_name} to markdown, length={len(result)}")
		return result

	def _get_extension(self, file_name: str) -> str:
		"""Extract lowercase file extension."""
		if "." not in file_name:
			raise ValueError(f"File has no extension: {file_name}")
		return "." + file_name.rsplit(".", 1)[-1].lower()


# Global singleton instance
document_flattener = DocumentFlatteningEngine()