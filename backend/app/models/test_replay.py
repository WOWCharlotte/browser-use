"""
Pydantic models for Test Replay management.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReplayRequest(BaseModel):
	"""Request model for starting a replay."""
	model_config = ConfigDict(extra='forbid')

	new_variables: dict[str, str] | None = Field(default=None, description="替换的变量值（null=使用原始变量）")
	mode: Literal["hybrid"] = Field(default='hybrid', description="重放模式：hybrid（混合）")


class TestReplayView(BaseModel):
	"""Response model for a test replay."""
	model_config = ConfigDict(extra='forbid')

	id: str
	result_id: str
	variables_json: str | None
	status: str
	mode: str
	fallback_count: int
	trajectory_path: str | None
	started_at: str
	completed_at: str | None
