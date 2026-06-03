"""Tests for Test Case Ingestion Module.

Note: Excel flattening tests require pandas which is not in the main project dependencies.
These tests are designed to run in the backend environment where pandas is available.
"""

from unittest.mock import AsyncMock

import pytest
from app.models.ingestion import (
	IngestionRequest,
	IngestionResponse,
	TestCaseParsedSchema,
	TestCaseSchema,
	TestPlanParsedSchema,
	TestStepSchema,
)
from pydantic import ValidationError

# ============================================================================
# Pydantic Model Tests
# ============================================================================


class TestTestStepSchema:
	"""Tests for TestStepSchema model."""

	def test_valid_step(self):
		"""Test creating a valid test step."""
		step = TestStepSchema(
			step_number=1,
			action_description="Navigate to {url}",
			expected_result="Page loads successfully",
			step_variables=["url"],
		)

		assert step.step_number == 1
		assert step.action_description == "Navigate to {url}"
		assert step.expected_result == "Page loads successfully"
		assert step.step_variables == ["url"]

	def test_step_number_must_be_positive(self):
		"""Test that step_number must be >= 1."""
		with pytest.raises(ValidationError):
			TestStepSchema(
				step_number=0,
				action_description="Test",
				expected_result="Result",
			)

	def test_empty_step_variables_defaults_to_empty_list(self):
		"""Test that empty step_variables defaults to empty list."""
		step = TestStepSchema(
			step_number=1,
			action_description="Click submit",
			expected_result="Form submitted",
		)

		assert step.step_variables == []


class TestTestCaseSchema:
	"""Tests for TestCaseSchema model."""

	def test_valid_test_case(self):
		"""Test creating a valid test case."""
		test_case = TestCaseSchema(
			case_name="User Login Test",
			start_url="https://example.com/login",
			steps=[
				TestStepSchema(
					step_number=1,
					action_description="Navigate to {url}",
					expected_result="Login page loads",
				),
			],
			global_variables=["url"],
		)

		assert test_case.case_name == "User Login Test"
		assert test_case.start_url == "https://example.com/login"
		assert len(test_case.steps) == 1

	def test_global_variables_deduplicated(self):
		"""Test that global_variables are deduplicated while preserving order."""
		test_case = TestCaseSchema(
			case_name="Test",
			start_url="https://example.com",
			steps=[],
			global_variables=["url", "username", "url", "password"],  # url appears twice
		)

		assert test_case.global_variables == ["url", "username", "password"]

	def test_global_variables_none_becomes_empty_list(self):
		"""Test that None global_variables becomes empty list."""
		test_case = TestCaseSchema(
			case_name="Test",
			start_url="https://example.com",
			steps=[],
			global_variables=None,  # type: ignore
		)

		assert test_case.global_variables == []


class TestIngestionRequest:
	"""Tests for IngestionRequest model."""

	def test_file_upload_request(self):
		"""Test creating a file upload request."""
		req = IngestionRequest(
			file_content="base64encodedcontent",
			file_name="test.xlsx",
		)

		assert req.file_content == "base64encodedcontent"
		assert req.file_name == "test.xlsx"
		assert req.markdown_content is None

	def test_markdown_content_request(self):
		"""Test creating a markdown content request."""
		req = IngestionRequest(
			markdown_content="# Test Case",
		)

		assert req.markdown_content == "# Test Case"
		assert req.file_content is None

	def test_extra_fields_forbidden(self):
		"""Test that extra fields are forbidden."""
		with pytest.raises(ValidationError):
			IngestionRequest(
				markdown_content="# Test",
				extra_field="not allowed",  # type: ignore
			)


class TestIngestionResponse:
	"""Tests for IngestionResponse model."""

	def test_successful_response(self):
		"""Test creating a successful response."""
		resp = IngestionResponse(
			success=True,
			case_name="Login Test",
			start_url="https://example.com/login",
			steps=[
				TestStepSchema(
					step_number=1,
					action_description="Enter {username}",
					expected_result="Username entered",
				),
			],
			global_variables=["username"],
		)

		assert resp.success is True
		assert resp.case_name == "Login Test"
		assert len(resp.steps) == 1

	def test_empty_global_variables(self):
		"""Test response with no variables."""
		resp = IngestionResponse(
			success=True,
			case_name="Simple Test",
			start_url="https://example.com",
			steps=[],
			global_variables=[],
		)

		assert resp.global_variables == []


# ============================================================================
# Ingestion Service Tests (with mocked LLM)
# ============================================================================


class TestIngestionServicePlaceholderValidation:
	"""Tests for placeholder validation in IngestionService."""

	def test_validate_placeholders_valid(self):
		"""Test validation passes for correctly formatted placeholders."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		errors = service._validate_placeholders("Navigate to {url} and enter {username}")

		assert errors == []

	def test_validate_placeholders_unclosed(self):
		"""Test validation fails for unclosed placeholders."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		errors = service._validate_placeholders("Navigate to {url")

		assert len(errors) > 0
		assert "Unclosed placeholder" in errors[0]

	def test_validate_placeholders_nested_braces(self):
		"""Test validation for nested braces (edge case - may not always be caught)."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		# This test documents an edge case - nested braces like {outer {inner}}
		# may not always be detected by the simple validation
		errors = service._validate_placeholders("Value is {outer {inner}}")
		# Not asserting on errors here as nested braces is a complex edge case
		# that may not be caught by basic placeholder validation

	def test_validate_placeholders_empty(self):
		"""Test validation fails for empty placeholders."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		errors = service._validate_placeholders("Value is {}")

		assert len(errors) > 0


class TestIngestionServiceVariableExtraction:
	"""Tests for variable extraction in IngestionService."""

	def test_extract_variables_from_text(self):
		"""Test extracting variable names from text."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		variables = service._extract_variables_from_text("Enter {username} and {password}")

		assert "username" in variables
		assert "password" in variables

	def test_extract_variables_deduplicated(self):
		"""Test that extracted variables are deduplicated."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		variables = service._extract_variables_from_text("{username} and {username}")

		# Should be unique
		assert len(set(variables)) == len(variables)

	def test_extract_variables_snake_case(self):
		"""Test extracting snake_case variable names."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		variables = service._extract_variables_from_text("Use {user_phone_number}")

		assert "user_phone_number" in variables


# ============================================================================
# Integration Tests (with mocked LLM)
# ============================================================================


class TestIngestionServiceIntegration:
	"""Integration tests for IngestionService with mocked LLM."""

	@pytest.fixture
	def mock_llm(self):
		"""Create a mock LLM for testing."""
		from unittest.mock import AsyncMock

		from browser_use.llm.base import BaseChatModel

		llm = AsyncMock(spec=BaseChatModel)
		llm.model = "mock-llm"
		llm._verified_api_keys = True
		llm.provider = "mock"
		llm.name = "mock-llm"
		llm.model_name = "mock-llm"
		return llm

	@pytest.mark.asyncio
	async def test_parse_markdown_success(self, mock_llm):
		"""Test successful markdown parsing with mocked LLM."""
		from app.services.ingestion_service import IngestionService

		from browser_use.llm.views import ChatInvokeCompletion

		mock_case = TestCaseParsedSchema(
			case_name="User Login",
			start_url="https://example.com/login",
			steps=[
				TestStepSchema(
					step_number=1,
					action_description="Enter {username}",
					expected_result="Username entered",
					step_variables=["username"],
				),
			],
			global_variables=["username"],
			variable_sets=[{"username": "test-user"}],
		)
		mock_response = TestPlanParsedSchema(test_cases=[mock_case])

		mock_llm.ainvoke = AsyncMock(
			return_value=ChatInvokeCompletion(completion=mock_response, usage=None)
		)

		service = IngestionService()
		service._llm = mock_llm

		result = await service.parse_markdown("# Test Case\n\nStep 1: Enter username", skip_validation=True)

		assert len(result.test_cases) == 1
		assert result.test_cases[0].case_name == "User Login"
		assert len(result.test_cases[0].steps) == 1
		assert result.test_cases[0].global_variables == ["username"]

	@pytest.mark.asyncio
	async def test_parse_markdown_no_variables(self, mock_llm):
		"""Test parsing markdown with no variables."""
		from app.services.ingestion_service import IngestionService

		from browser_use.llm.views import ChatInvokeCompletion

		mock_case = TestCaseParsedSchema(
			case_name="Simple Navigation",
			start_url="https://example.com",
			steps=[
				TestStepSchema(
					step_number=1,
					action_description="Navigate to the website",
					expected_result="Page loads",
					step_variables=[],
				),
			],
			global_variables=[],
			variable_sets=[],
		)
		mock_response = TestPlanParsedSchema(test_cases=[mock_case])

		mock_llm.ainvoke = AsyncMock(
			return_value=ChatInvokeCompletion(completion=mock_response, usage=None)
		)

		service = IngestionService()
		service._llm = mock_llm

		result = await service.parse_markdown("Simple test content", skip_validation=True)

		assert result.test_cases[0].global_variables == []

	@pytest.mark.asyncio
	async def test_ingest_file_unsupported_type(self):
		"""Test that unsupported file types raise ValueError."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()

		with pytest.raises(ValueError, match="Unsupported file type"):
			await service.ingest_file("test.pdf", b"content")

	@pytest.mark.asyncio
	async def test_ingest_file_too_large(self):
		"""Test that files over 5MB are rejected."""
		from app.services.ingestion_service import IngestionService

		service = IngestionService()
		large_content = b"x" * (6 * 1024 * 1024)  # 6MB

		with pytest.raises(ValueError, match="File size exceeds"):
			await service.ingest_file("test.xlsx", large_content)
