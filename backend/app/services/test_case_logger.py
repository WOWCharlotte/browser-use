"""
TestCaseLogger — Per-case execution log writer.

Each test case execution gets its own log file at:
  data/trajectories/{run_id}/{case_id}_{set_index}.log
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import Config


class TestCaseLogger:
	"""Structured logger for a single test case execution."""

	def __init__(self, run_id: str, case_id: str, set_index: int = 0) -> None:
		self._run_id = run_id
		self._case_id = case_id
		self._set_index = set_index

		self._log_dir = Config.TRAJECTORY_DIR / run_id
		self._log_dir.mkdir(parents=True, exist_ok=True)

		self._log_path = self._log_dir / f"{case_id}_{set_index}.log"
		self._handler: logging.FileHandler | None = None
		self._logger = self._create_logger()

	def _create_logger(self) -> logging.Logger:
		logger_name = f"test_case.{self._run_id}.{self._case_id}.{self._set_index}"
		logger = logging.getLogger(logger_name)
		logger.setLevel(logging.DEBUG)
		logger.propagate = False

		handler = logging.FileHandler(str(self._log_path), encoding="utf-8")
		handler.setLevel(logging.DEBUG)
		formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
		handler.setFormatter(formatter)
		logger.addHandler(handler)

		self._handler = handler
		return logger

	@property
	def log_path(self) -> Path:
		return self._log_path

	def info(self, message: str) -> None:
		self._logger.info(message)

	def warn(self, message: str) -> None:
		self._logger.warning(message)

	def error(self, message: str) -> None:
		self._logger.error(message)

	def debug(self, message: str) -> None:
		self._logger.debug(message)

	def close(self) -> None:
		if self._handler:
			self._handler.close()
			self._logger.removeHandler(self._handler)
			self._handler = None
