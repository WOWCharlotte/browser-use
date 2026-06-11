import base64
import logging
from dataclasses import dataclass

from ag_ui.core import RunAgentInput
from ag_ui.core.types import DocumentInputContent, InputContentDataSource, TextInputContent

logger = logging.getLogger(__name__)


@dataclass
class ExtractedInput:
	text: str
	attachments: list[tuple[str, bytes, str]]


def extract_input(input_data: RunAgentInput) -> ExtractedInput:
	"""Extract user text and document attachments from AG-UI input."""
	text = ""
	attachments: list[tuple[str, bytes, str]] = []

	if not input_data.messages:
		return ExtractedInput(text=text, attachments=attachments)

	last_msg = input_data.messages[-1]
	if not (hasattr(last_msg, "role") and last_msg.role == "user"):
		return ExtractedInput(text=text, attachments=attachments)

	content = getattr(last_msg, "content", "")
	if isinstance(content, str):
		return ExtractedInput(text=content, attachments=attachments)

	for part in content:
		if isinstance(part, TextInputContent):
			text = part.text
		elif isinstance(part, DocumentInputContent):
			source = part.source
			if not isinstance(source, InputContentDataSource):
				continue
			meta = part.metadata or {}
			filename = meta.get("filename") or meta.get("name") or "upload"
			try:
				file_bytes = base64.b64decode(source.value)
			except Exception as exc:
				logger.warning("Failed to decode attachment '%s': %s", filename, exc)
				continue
			attachments.append((filename, file_bytes, source.mime_type))

	return ExtractedInput(text=text, attachments=attachments)


def extract_task(input_data: RunAgentInput) -> str:
	"""Extract user task text from AG-UI input."""
	return extract_input(input_data).text
