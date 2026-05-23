"""
Pydantic models for Test Plan management.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.ingestion import TestStepSchema


class TestPlanCreate(BaseModel):
	"""Request model for creating a test plan."""
	model_config = ConfigDict(extra='forbid')

	name: str = Field(..., description="计划名称")
	description: str | None = Field(default=None, description="计划描述")
	source_file_name: str | None = Field(default=None, description="来源文件名")
	max_concurrency: int = Field(default=3, ge=1, le=5, description="最大并发数")


class TestPlanUpdate(BaseModel):
	"""Request model for updating a test plan."""
	model_config = ConfigDict(extra='forbid')

	name: str | None = Field(default=None, description="计划名称")
	description: str | None = Field(default=None, description="计划描述")
	max_concurrency: int | None = Field(default=None, ge=1, le=5, description="最大并发数")


class TestPlanView(BaseModel):
	"""Response model for a test plan."""
	model_config = ConfigDict(extra='forbid')

	id: str
	name: str
	description: str | None
	source_file_name: str | None
	max_concurrency: int
	status: str
	created_at: str
	updated_at: str


class TestCaseCreate(BaseModel):
	"""Request model for creating a test case."""
	model_config = ConfigDict(extra='forbid')

	case_name: str = Field(..., description="用例名称")
	description: str | None = Field(default=None)
	module: str | None = Field(default=None)
	function_point: str | None = Field(default=None)
	start_url: str = Field(..., description="起始 URL")
	steps: list[TestStepSchema] = Field(..., description="测试步骤")
	global_variables: list[str] = Field(default=[], description="全局变量名")
	variable_values: dict[str, str] = Field(default={}, description="默认变量值")
	execution_order: int | None = Field(default=None)


class TestCaseUpdate(BaseModel):
	"""Request model for updating a test case."""
	model_config = ConfigDict(extra='forbid')

	case_name: str | None = Field(default=None)
	description: str | None = Field(default=None)
	module: str | None = Field(default=None)
	function_point: str | None = Field(default=None)
	start_url: str | None = Field(default=None)
	steps: list[TestStepSchema] | None = Field(default=None)
	global_variables: list[str] | None = Field(default=None)
	variable_values: dict[str, str] | None = Field(default=None)
	execution_order: int | None = Field(default=None)


class TestCaseView(BaseModel):
	"""Response model for a test case."""
	model_config = ConfigDict(extra='forbid')

	id: str
	plan_id: str
	case_name: str
	description: str | None
	module: str | None
	function_point: str | None
	start_url: str
	steps: list[TestStepSchema]
	global_variables: list[str]
	variable_values: dict[str, str]
	status: str
	execution_order: int | None
	created_at: str
	updated_at: str


class VariableSetView(BaseModel):
	"""Response model for a variable set."""
	model_config = ConfigDict(extra='forbid')

	id: str
	case_id: str
	set_index: int
	variables: dict[str, str]
	status: str
	created_at: str


class VariableImportRequest(BaseModel):
	"""Request model for importing variable sets."""
	model_config = ConfigDict(extra='forbid')

	variable_sets: list[dict[str, str]] = Field(..., description="变量集列表，每组为 {变量名: 值} 字典")


class TestPlanDetailView(BaseModel):
	"""Response model for test plan with cases."""
	model_config = ConfigDict(extra='forbid')

	id: str
	name: str
	description: str | None
	source_file_name: str | None
	max_concurrency: int
	status: str
	created_at: str
	updated_at: str
	cases: list[TestCaseView] = Field(default=[])
