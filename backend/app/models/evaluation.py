"""
Evaluation models — Structured output for LLM-based test result evaluation.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CheckpointEvaluation(BaseModel):
	"""Evaluation result for a single checkpoint (step with expected_result)."""

	model_config = ConfigDict(extra="forbid")

	step_number: int = Field(description="步骤编号")
	expected_result: str = Field(description="预期结果")
	actual_observation: str = Field(description="实际观察到的结果")
	verdict: Literal["pass", "fail", "inconclusive"] = Field(
		description="判定: pass=符合预期, fail=不符合预期, inconclusive=无法判断"
	)
	reasoning: str = Field(description="判定理由")


class EvaluationResult(BaseModel):
	"""Complete evaluation result for a test case execution."""

	model_config = ConfigDict(extra="forbid")

	overall_status: Literal["passed", "failed", "error"] = Field(
		description="整体结论: passed=所有检查点通过, failed=任一检查点失败, error=评估过程出错"
	)
	checkpoints: list[CheckpointEvaluation] = Field(
		default_factory=list, description="各检查点评估结果"
	)
	execution_errors: list[str] = Field(
		default_factory=list, description="执行过程中的异常（非检查点相关）"
	)
	summary: str = Field(description="评估总结（一句话概括）")
