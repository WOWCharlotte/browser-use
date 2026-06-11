"""Tests for observability module."""

import importlib
import os
import sys
import types
from unittest.mock import patch

from browser_use.observability import (
	get_observability_status,
	is_debug_mode,
	is_lmnr_available,
	observe,
	observe_debug,
)


def test_observability_status_no_lmnr():
	"""Test status when lmnr is not available."""
	with patch.dict(os.environ, {'LMNR_LOGGING_LEVEL': ''}, clear=False):
		# Force re-check of lmnr availability by mocking
		with patch('browser_use.observability._LMNR_AVAILABLE', False):
			status = get_observability_status()
			assert 'lmnr_available' in status
			assert 'debug_mode' in status


def test_debug_mode_env_var():
	"""Test that LMNR_LOGGING_LEVEL=debug enables debug mode."""
	with patch.dict(os.environ, {'LMNR_LOGGING_LEVEL': 'debug'}, clear=False):
		# Force re-evaluation
		assert is_debug_mode() is True


def test_debug_mode_disabled():
	"""Test that debug mode is disabled when env var is not set."""
	with patch.dict(os.environ, {'LMNR_LOGGING_LEVEL': ''}, clear=False):
		assert is_debug_mode() is False


def test_observe_decorator():
	"""Test that observe decorator works (returns a callable)."""

	@observe(name='test_func')
	def test_func():
		return 42

	result = test_func()
	assert result == 42


def test_observe_debug_decorator():
	"""Test that observe_debug decorator works."""

	@observe_debug(name='test_debug_func', ignore_input=True, ignore_output=True)
	def test_debug_func():
		return 'debugged'

	result = test_debug_func()
	assert result == 'debugged'


def test_observe_decorator_async():
	"""Test observe decorator on async functions."""

	@observe(name='test_async')
	async def test_async():
		return await asyncio.sleep(0, result=42)

	import asyncio

	result = asyncio.get_event_loop().run_until_complete(test_async())
	assert result == 42


def test_lmnr_available_check():
	"""Test that is_lmnr_available returns current state."""
	# Just call it - actual value depends on whether lmnr is installed
	result = is_lmnr_available()
	assert isinstance(result, bool)


def test_laminar_initialized_when_project_api_key_is_set(monkeypatch):
	"""Test that Laminar tracing is initialized when LMNR_PROJECT_API_KEY is set."""
	initialize_calls = []

	fake_lmnr = types.ModuleType('lmnr')

	def fake_observe(**kwargs):
		def decorator(func):
			return func

		return decorator

	class FakeLaminar:
		@staticmethod
		def initialize(project_api_key: str):
			initialize_calls.append(project_api_key)

	fake_lmnr.observe = fake_observe
	fake_lmnr.Laminar = FakeLaminar

	monkeypatch.setitem(sys.modules, 'lmnr', fake_lmnr)
	monkeypatch.setenv('LMNR_PROJECT_API_KEY', 'test-project-key')

	import browser_use.observability as observability

	importlib.reload(observability)

	assert initialize_calls == ['test-project-key']
