"""Global logging configuration for the backend service."""

from __future__ import annotations

import logging
import os
import sys

BACKEND_CONSOLE_HANDLER_NAME = "browser-use-backend-console"
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_log_level(level_name: str | None = None) -> int:
	normalized = (level_name or os.getenv("LOG_LEVEL") or DEFAULT_LOG_LEVEL).strip().upper()
	level = logging.getLevelName(normalized)
	if isinstance(level, int):
		return level
	return logging.INFO


def configure_logging(level_name: str | None = None) -> None:
	"""Configure process-wide console logging.

	Default level is INFO. Set LOG_LEVEL=DEBUG/WARNING/ERROR/etc. to override.
	The function is idempotent and updates the existing backend console handler
	instead of adding duplicates.
	"""
	level = _resolve_log_level(level_name)
	root_logger = logging.getLogger()
	root_logger.setLevel(level)

	formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
	console_handler = next(
		(
			handler
			for handler in root_logger.handlers
			if getattr(handler, "name", None) == BACKEND_CONSOLE_HANDLER_NAME
		),
		None,
	)

	if console_handler is None:
		console_handler = logging.StreamHandler(sys.stdout)
		console_handler.name = BACKEND_CONSOLE_HANDLER_NAME
		root_logger.addHandler(console_handler)

	console_handler.setLevel(level)
	console_handler.setFormatter(formatter)
