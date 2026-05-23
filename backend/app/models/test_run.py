"""
Pydantic models for Test Run and Result management.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TestRunCreate(BaseModel):
	"""Request model for starting a test run."""
	model_config = ConfigDict(extra='forbid')

	plan_id: str = Field(..., description="测试计划 ID")
	max_concurrency: int = Field(default=3, ge=1, le=5, description="最大并发数")
	max_retries: int = Field(default=1, ge=1, description="最大重试次数（1=不重试）")
	case_timeout_seconds: int = Field(default=600, ge=30, description="单用例超时秒数")
	case_ids: list[str] | None = Field(default=None, description="选择性执行的用例 ID 列表（null=全部）")
	rerun_failed: str | None = Field(default=None, description="重跑指定 run_id 中失败的用例")


class TestRunView(BaseModel):
	"""Response model for a test run."""
	model_config = ConfigDict(extra='forbid')

	id: str
	plan_id: str
	status: str
	max_concurrency: int
	max_retries: int
	case_timeout_seconds: int
	case_ids_filter: str | None
	rerun_of_run_id: str | None
	total_cases: int
	passed_cases: int
	failed_cases: int
	error_cases: int
	started_at: str
	completed_at: str | None


class TestResultView(BaseModel):
	"""Response model for a test result."""
	model_config = ConfigDict(extra='forbid')

	id: str
	run_id: str
	case_id: str
	variable_set_id: str | None
	session_id: str | None
	status: str
	actual_result: str | None
	evaluation: str | None
	evaluation_details: str | None
	error_message: str | None
	duration_seconds: float | None
	retry_count: int
	case_snapshot_json: str | None
	original_status: str | None
	override_reason: str | None
	trajectory_path: str | None
	started_at: str | None
	completed_at: str | None


class OverrideRequest(BaseModel):
	"""Request model for manually overriding a test result."""
	model_config = ConfigDict(extra='forbid')

	status: Literal["passed", "failed"] = Field(..., description="覆盖后的状态：passed 或 failed")
	reason: str = Field(..., description="覆盖原因")
