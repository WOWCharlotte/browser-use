"""
Test Case Ingestion Service.

Provides LLM-powered parsing of test cases from unstructured documents,
extracting steps, actions, expected results, and dynamic variables.
"""

import logging
import re
from typing import Any

from app.config import Config
from app.models.ingestion import TestCaseSchema, TestStepSchema
from app.services.document_flattening import document_flattener
from browser_use.llm.messages import SystemMessage, UserMessage
from browser_use.llm.openai.chat import ChatOpenAI

logger = logging.getLogger(__name__)


# System prompt for test case extraction
TEST_CASE_EXTRACTION_PROMPT = """你是一个专业的测试用例分析助手。你的任务是从用户提供的测试用例文档中提取结构化的测试步骤和变量信息。

## 输入格式
用户会提供一个测试用例文档（Markdown格式），包含测试步骤、操作描述和预期结果。

## 输出要求
你必须输出一个完全符合下面JSON Schema的JSON对象，不要包含任何其他文字：

```json
{
  "case_name": "string",  // 提炼出能够代表此测试用例的核心唯一业务名称
  "start_url": "string",  // 该自动化测试执行的起始目标URL。如果用例中未提供，需要根据上下文进行常识性合理推理猜测
  "steps": [
    {
      "step_number": number,  // 操作步骤的自增序号，从1开始
      "action_description": "string",  // 具体的浏览器操作指令描述。如果发现步骤中包含可变参数（如特定的用户名、手机号、动态日期等），请将其统一转化为英文花括号占位符格式，例如：'在输入框输入 {username}'
      "expected_result": "string",  // 当前步骤操作完成后，页面应达到的预期状态断言目标
      "step_variables": ["string"]  // 本步骤中被抽离并转化为花括号占位符的变量名清单
    }
  ],
  "global_variables": ["string"]  // 整个测试用例中所有步骤涉及的变量的全局去重汇总清单
}
```

## 变量提取规则
1. **语义识别**：识别测试数据实体，如测试账号、手机号、商品ID、日期等
2. **占位符转换**：将可变参数替换为英文花括号命名占位符，如 {user_phone}, {sku_id}
3. **一致性**：相同含义的变量在不同步骤中必须使用完全相同的占位符名称
4. **全局汇总**：在 global_variables 中输出所有变量的去重清单

## 重要约束
- action_description 中的所有占位符必须格式正确：{variable_name}，左右花括号缺一不可
- global_variables 中的变量名不应包含花括号，只包含变量名本身
- 如果测试用例中没有变量，global_variables 返回空数组 []
- 如果没有提供start_url，根据上下文合理推断（如 https://github.com/login）
"""


class IngestionService:
	"""Service for ingesting and parsing test cases from documents."""

	MAX_RETRIES = 2
	MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

	def __init__(self) -> None:
		self._llm: ChatOpenAI | None = None

	def _get_llm(self) -> ChatOpenAI:
		"""Get or create LLM client."""
		if self._llm is None:
			logger.debug("Initializing LLM client for ingestion service")
			self._llm = ChatOpenAI(
				model=Config.LLM_MODEL,
				api_key=Config.LLM_API_KEY,
				base_url=Config.LLM_BASE_URL,
				temperature=0.2,
			)
		return self._llm

	def _validate_placeholders(self, text: str) -> list[str]:
		"""
		Validate that all placeholders in text are properly closed.

		Returns list of validation errors (empty if valid).
		"""
		errors = []

		# Check for unclosed placeholders (text with { but no proper closing })
		# Pattern: { followed by any non-} characters, then end of string
		if re.search(r"\{[^}]*$", text):
			errors.append(f"Unclosed placeholder detected")

		# Check for empty braces {}
		if re.search(r"\{\}", text):
			errors.append("Empty placeholder: {}")

		return errors

	def _validate_test_case(self, test_case: TestCaseSchema) -> list[str]:
		"""
		Validate a parsed TestCaseSchema.

		Returns list of validation errors (empty if valid).
		"""
		errors = []

		# Validate all placeholders in step descriptions
		for step in test_case.steps:
			placeholder_errors = self._validate_placeholders(step.action_description)
			errors.extend([f"Step {step.step_number} action: {e}" for e in placeholder_errors])

			# Validate expected_result only if it exists
			if step.expected_result is not None:
				placeholder_errors = self._validate_placeholders(step.expected_result)
				errors.extend([f"Step {step.step_number} expected_result: {e}" for e in placeholder_errors])

		return errors

	def _extract_variables_from_text(self, text: str|None) -> list[str]:
		"""
		Extract variable names from placeholder patterns in text.

		Returns list of unique variable names (without braces).
		"""
		if not text:
			return []
		placeholder_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
		return list(set(re.findall(placeholder_pattern, text)))

	async def parse_markdown(
		self,
		markdown_content: str,
		skip_validation: bool = False,
	) -> TestCaseSchema:
		"""
		Parse markdown content into structured test case using LLM.

		Args:
			markdown_content: Flattened markdown text from document
			skip_validation: Skip placeholder validation (for testing)

		Returns:
			Structured TestCaseSchema

		Raises:
			ValueError: If parsing fails or validation errors after retries
		"""
		llm = self._get_llm()
		content_preview = markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
		logger.info(f"Parsing markdown content: {content_preview}")

		messages = [
			SystemMessage(content=TEST_CASE_EXTRACTION_PROMPT),
			UserMessage(content=markdown_content),
		]

		# Try parsing with retry for malformed output
		last_error: Exception | None = None
		for attempt in range(self.MAX_RETRIES + 1):
			try:
				logger.info(f"LLM invocation attempt {attempt + 1}/{self.MAX_RETRIES + 1}")
				response = await llm.ainvoke(messages, output_format=TestCaseSchema)
				test_case = response.completion
				logger.info(f"LLM response received: case_name={test_case.case_name}, steps_count={len(test_case.steps)}")

				# Validate placeholders
				if not skip_validation:
					validation_errors = self._validate_test_case(test_case)
					if validation_errors:
						logger.warning(f"Placeholder validation failed: {validation_errors}")
						if attempt < self.MAX_RETRIES:
							# Retry with error feedback
							messages = [
								SystemMessage(content=TEST_CASE_EXTRACTION_PROMPT),
								UserMessage(
									content=(
										f"Previous attempt had errors:\n"
										f"{chr(10).join(validation_errors)}\n\n"
										f"Please correct and re-parse:\n{markdown_content}"
									)
								),
							]
							continue
						else:
							raise ValueError(f"Placeholder validation failed after {self.MAX_RETRIES} retries: {validation_errors}")

				# Ensure global_variables are consistent with actual placeholders used
				all_step_vars = []
				for step in test_case.steps:
					all_step_vars.extend(self._extract_variables_from_text(step.action_description))
					all_step_vars.extend(self._extract_variables_from_text(step.expected_result))
					step.step_variables = list(set(step.step_variables))

				# Update global_variables to be the union of all extracted variables
				test_case.global_variables = sorted(list(set(all_step_vars)))

				logger.info(f"Successfully parsed test case: {test_case.case_name}, global_variables={test_case.global_variables}")
				return test_case

			except Exception as e:
				last_error = e
				logger.warning(f"Attempt {attempt + 1} failed: {e}")
				if attempt < self.MAX_RETRIES:
					continue

		raise ValueError(f"Failed to parse test case after {self.MAX_RETRIES + 1} attempts: {last_error}")

	async def ingest_file(
		self,
		file_name: str,
		file_content: bytes,
	) -> TestCaseSchema:
		"""
		Ingest a document file and parse into structured test case.

		Args:
			file_name: Original file name with extension
			file_content: Raw file bytes

		Returns:
			Structured TestCaseSchema

		Raises:
			ValueError: If file type not supported or parsing fails
		"""
		logger.info(f"Ingesting file: {file_name}, size={len(file_content)} bytes")

		# Check file size
		if len(file_content) > self.MAX_FILE_SIZE:
			raise ValueError(f"File size exceeds maximum of {self.MAX_FILE_SIZE // (1024*1024)}MB")

		# Check if supported
		if not document_flattener.is_supported(file_name):
			raise ValueError(
				f"Unsupported file type: {file_name}. Supported types: .xlsx, .xls, .md, .markdown"
			)

		# Flatten document
		markdown = document_flattener.flatten(file_name, file_content)
		logger.debug(f"Document flattened successfully, markdown length={len(markdown)}")

		# Parse with LLM
		return await self.parse_markdown(markdown)

	async def ingest_markdown(
		self,
		markdown_content: str,
	) -> TestCaseSchema:
		"""
		Ingest markdown content directly and parse into structured test case.

		Args:
			markdown_content: Raw markdown text

		Returns:
			Structured TestCaseSchema
		"""
		logger.info(f"Ingesting markdown content, length={len(markdown_content)}")
		return await self.parse_markdown(markdown_content)


# Global singleton instance
ingestion_service = IngestionService()