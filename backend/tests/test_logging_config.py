"""Tests for global backend logging configuration."""

import logging

from app.logging_config import BACKEND_CONSOLE_HANDLER_NAME, configure_logging


def _remove_backend_handlers() -> None:
	root_logger = logging.getLogger()
	for handler in list(root_logger.handlers):
		if getattr(handler, "name", None) == BACKEND_CONSOLE_HANDLER_NAME:
			root_logger.removeHandler(handler)


def test_configure_logging_defaults_root_logger_to_info(monkeypatch):
	monkeypatch.delenv("LOG_LEVEL", raising=False)
	root_logger = logging.getLogger()
	original_level = root_logger.level
	try:
		_remove_backend_handlers()
		root_logger.setLevel(logging.WARNING)

		configure_logging()

		assert root_logger.level == logging.INFO
		assert any(
			getattr(handler, "name", None) == BACKEND_CONSOLE_HANDLER_NAME
			and handler.level == logging.INFO
			for handler in root_logger.handlers
		)
	finally:
		_remove_backend_handlers()
		root_logger.setLevel(original_level)


def test_configure_logging_uses_log_level_env(monkeypatch):
	monkeypatch.setenv("LOG_LEVEL", "DEBUG")
	root_logger = logging.getLogger()
	original_level = root_logger.level
	try:
		_remove_backend_handlers()

		configure_logging()

		assert root_logger.level == logging.DEBUG
		assert any(
			getattr(handler, "name", None) == BACKEND_CONSOLE_HANDLER_NAME
			and handler.level == logging.DEBUG
			for handler in root_logger.handlers
		)
	finally:
		_remove_backend_handlers()
		root_logger.setLevel(original_level)


def test_configure_logging_is_idempotent(monkeypatch):
	monkeypatch.delenv("LOG_LEVEL", raising=False)
	root_logger = logging.getLogger()
	original_level = root_logger.level
	try:
		_remove_backend_handlers()

		configure_logging()
		configure_logging()

		backend_handlers = [
			handler
			for handler in root_logger.handlers
			if getattr(handler, "name", None) == BACKEND_CONSOLE_HANDLER_NAME
		]
		assert len(backend_handlers) == 1
	finally:
		_remove_backend_handlers()
		root_logger.setLevel(original_level)
