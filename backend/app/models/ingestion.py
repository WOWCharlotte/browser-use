"""
Pydantic models for the Test Case Ingestion Module.

This module defines the schema for parsing test cases from Excel/Markdown documents
into structured test steps with variable extraction.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TestStepSchema(BaseModel):
	"""Represents a single test step with action and expected result."""

	step_number: int = Field(..., description="操作步骤的自增序号，从 1 开始")
	action_description: str = Field(
		...,
		description="具体的浏览器操作指令描述。如果发现步骤中包含可变参数（如特定的用户名、手机号、动态日期等），"
		"请将其统一转化为英文花括号占位符格式，例如：'在输入框输入 {username}'。保持占位符名称具有明确的业务含义。",
	)
	expected_result: str | None = Field(
		default=None,
		description="当前步骤操作完成后，页面应达到的预期状态断言目标。如果没有预期结果，可为空",
	)
	step_variables: list[str] = Field(
		default=[],
		description="本步骤中被抽离并转化为花括号占位符的变量名清单。如果没有变量，返回空列表。例如：['username']",
	)
	is_visual_checkpoint: bool = Field(default=False, description="是否为视觉检查点，需要截图辅助评估")

	@field_validator("step_number")
	@classmethod
	def validate_step_number(cls, v: int) -> int:
		if v < 1:
			raise ValueError("step_number must start from 1")
		return v


class TestCaseSchema(BaseModel):
	"""Represents a complete test case with steps and global variables."""

	case_name: str = Field(..., description="提炼出能够代表此测试用例的唯一业务名称")
	start_url: str = Field(
		...,
		description="该自动化测试执行的起始目标 URL。如果用例中未提供，模型需要根据上下文进行常识性合理推理猜测（例如：https://github.com）",
	)
	steps: list[TestStepSchema] = Field(..., description="按执行逻辑严格排序的细分操作步骤列表")
	global_variables: list[str] = Field(
		...,
		description="整个测试用例中所有步骤涉及的变量的全局去重汇总清单。例如：['username', 'password', 'sku_id']。",
	)

	@field_validator("global_variables", mode="before")
	@classmethod
	def validate_global_variables(cls, v: list[str]) -> list[str]:
		# Return empty list if None or empty
		if not v:
			return []
		# Ensure uniqueness while preserving order
		seen = set()
		unique = []
		for item in v:
			if item not in seen:
				seen.add(item)
				unique.append(item)
		return unique


class IngestionRequest(BaseModel):
	"""Request model for test case ingestion."""

	file_content: str | None = Field(None, description="Base64 encoded file content (for file upload)")
	file_name: str | None = Field(None, description="Original file name with extension")
	markdown_content: str | None = Field(None, description="Direct markdown text content (alternative to file upload)")

	model_config = ConfigDict(extra="forbid", validate_by_name=True)


class IngestionResponse(BaseModel):
	"""Response model for successful test case ingestion (single case, legacy)."""

	success: bool = True
	case_name: str
	start_url: str
	steps: list[TestStepSchema]
	global_variables: list[str]
	raw_markdown: str | None = Field(None, description="The flattened markdown text used for LLM parsing")


class IngestionErrorResponse(BaseModel):
	"""Response model for ingestion errors."""

	success: bool = False
	error: str
	code: str


class TestCaseParsedSchema(BaseModel):
	"""LLM 解析输出的单条用例（含合并后的变量集）"""
	model_config = ConfigDict(extra='forbid')

	case_name: str = Field(..., description="用例名称")
	description: str | None = Field(default=None, description="用例描述")
	module: str | None = Field(default=None, description="所属模块")
	function_point: str | None = Field(default=None, description="功能点")
	start_url: str = Field(..., description="起始 URL")
	steps: list[TestStepSchema] = Field(..., description="测试步骤列表")
	global_variables: list[str] = Field(default=[], description="全局变量名列表")
	variable_sets: list[dict[str, str]] = Field(default=[], description="变量集列表，至少 1 组")


class TestPlanParsedSchema(BaseModel):
	"""LLM 解析输出的完整结果（多条用例，已合并）"""
	model_config = ConfigDict(extra='forbid')

	test_cases: list[TestCaseParsedSchema] = Field(..., description="解析出的用例列表")


class PlanIngestionResponse(BaseModel):
	"""Response model for successful plan ingestion (multi-case)."""

	success: bool = True
	test_cases: list[TestCaseParsedSchema]
	total_cases: int
	raw_markdown: str | None = Field(None, description="The flattened markdown text used for LLM parsing")