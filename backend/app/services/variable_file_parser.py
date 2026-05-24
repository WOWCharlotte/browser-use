"""
Variable File Parser — parses CSV/Excel files into variable sets.

Each file row (after the header) becomes one variable set (dict[str, str]).
Used for bulk-importing parameterized test data into test cases.
"""

import csv
import io
import logging

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = frozenset({".csv", ".xlsx", ".xls"})
_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB


class VariableFileParser:
	"""Parses CSV or Excel files into a list of variable-set dicts."""

	def is_supported(self, file_name: str) -> bool:
		"""Return True if the file extension is supported."""
		return _get_extension(file_name) in _SUPPORTED_EXTENSIONS

	def parse(self, file_name: str, file_content: bytes) -> list[dict[str, str]]:
		"""
		Parse a CSV or Excel file into variable sets.

		Args:
			file_name: Original file name (used to detect format).
			file_content: Raw file bytes.

		Returns:
			List of dicts mapping variable name → value (all values are strings).

		Raises:
			ValueError: If the file type is unsupported, too large, has no header,
			            or has no data rows.
		"""
		if len(file_content) > _MAX_FILE_SIZE:
			raise ValueError(
				f"File size {len(file_content)} bytes exceeds the 2 MB limit"
			)

		ext = _get_extension(file_name)
		if ext not in _SUPPORTED_EXTENSIONS:
			raise ValueError(
				f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
			)

		if ext == ".csv":
			rows = self._parse_csv(file_content)
		else:
			rows = self._parse_excel(file_content)

		if not rows:
			raise ValueError("File contains no data rows (only a header or is empty)")

		logger.info(f"Parsed {len(rows)} variable sets from {file_name}")
		return rows

	# ── private ──────────────────────────────────────────────────────────────

	def _parse_csv(self, content: bytes) -> list[dict[str, str]]:
		"""Parse UTF-8 (with or without BOM) CSV bytes."""
		try:
			text = content.decode("utf-8-sig")  # strips BOM if present
		except UnicodeDecodeError as exc:
			raise ValueError(f"CSV file is not valid UTF-8: {exc}") from exc

		reader = csv.DictReader(io.StringIO(text))

		if reader.fieldnames is None:
			raise ValueError("CSV file has no header row")

		headers = [h.strip() for h in reader.fieldnames if h and h.strip()]
		if not headers:
			raise ValueError("CSV header row is empty")

		rows: list[dict[str, str]] = []
		for row in reader:
			# Skip completely blank rows
			values = [str(v).strip() if v is not None else "" for v in row.values()]
			if not any(values):
				continue
			rows.append({h: str(row.get(h) or "").strip() for h in headers})

		return rows

	def _parse_excel(self, content: bytes) -> list[dict[str, str]]:
		"""Parse the first sheet of an Excel file (.xlsx / .xls)."""
		try:
			import openpyxl  # already a project dependency via pandas/openpyxl
		except ImportError as exc:
			raise ValueError("openpyxl is required to parse Excel files") from exc

		try:
			wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
		except Exception as exc:
			raise ValueError(f"Failed to open Excel file: {exc}") from exc

		ws = wb.worksheets[0]
		all_rows = list(ws.iter_rows(values_only=True))
		wb.close()

		if not all_rows:
			raise ValueError("Excel file is empty")

		# First row is the header
		raw_headers = all_rows[0]
		headers = [str(h).strip() if h is not None else "" for h in raw_headers]
		headers = [h for h in headers if h]  # drop empty header cells

		if not headers:
			raise ValueError("Excel header row is empty")

		rows: list[dict[str, str]] = []
		for raw_row in all_rows[1:]:
			values = [str(v).strip() if v is not None else "" for v in raw_row]
			# Skip completely blank rows
			if not any(values):
				continue
			row_dict = {
				headers[i]: values[i] if i < len(values) else ""
				for i in range(len(headers))
			}
			rows.append(row_dict)

		return rows


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_extension(file_name: str) -> str:
	"""Return the lowercase file extension including the dot."""
	if "." not in file_name:
		return ""
	return "." + file_name.rsplit(".", 1)[-1].lower()


# Global singleton
variable_file_parser = VariableFileParser()
