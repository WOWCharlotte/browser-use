"""
Test Evaluation Service — LLM-based checkpoint evaluation for test results.

Evaluates test case execution by comparing trajectory against expected results
at checkpoint steps. Supports visual checkpoints via multimodal LLM.
"""

import base64
import json
import logging
from pathlib import Path
from typing import Any

from app.config import Config
from app.models.evaluation import CheckpointEvaluation, EvaluationResult

logger = logging.getLogger(__name__)

EVALUATION_SYSTEM_PROMPT = """\
你是一个自动化测试结果评估专家。你的任务是根据测试执行轨迹判断每个检查点是否通过。

## 评估规则

1. 对每个检查点，根据执行轨迹中的实际观察判定 pass/fail/inconclusive
2. pass: 实际结果明确符合预期
3. fail: 实际结果明确不符合预期，或执行过程中出现错误导致无法达到预期
4. inconclusive: 轨迹信息不足以判断（如页面未加载完成就超时）
5. 整体结论: 所有检查点 pass → passed; 任一 fail → failed; 全部 inconclusive → error

## 输出格式

严格按照 JSON 格式输出，不要添加任何额外文字：
{
  "overall_status": "passed" | "failed" | "error",
  "checkpoints": [
    {
      "step_number": 1,
      "expected_result": "预期结果文本",
      "actual_observation": "从轨迹中观察到的实际情况",
      "verdict": "pass" | "fail" | "inconclusive",
      "reasoning": "判定理由"
    }
  ],
  "execution_errors": ["执行过程中的异常列表，如超时、崩溃等"],
  "summary": "一句话总结评估结果"
}
"""


class TestEvaluationService:
	"""Evaluates test case execution results using LLM."""

	async def evaluate(
		self,
		history: Any,
		case: dict,
		screenshots_dir: Path | None = None,
	) -> EvaluationResult:
		"""Evaluate a test case execution against its checkpoints."""
		case_name = case.get("case_name", "unknown")
		logger.info(f"[{case_name}] 开始评估")

		try:
			checkpoints = self._extract_checkpoints(case)
			if not checkpoints:
				logger.info(f"[{case_name}] 无检查点，使用 Agent 自身判定")
				result = self._evaluate_without_checkpoints(history)
				logger.info(f"[{case_name}] 评估完成: {result.overall_status}")
				return result

			logger.info(f"[{case_name}] 提取到 {len(checkpoints)} 个检查点")

			trajectory_summary = self._build_trajectory_summary(history)
			logger.debug(f"[{case_name}] 轨迹摘要: {len(trajectory_summary)} 字符, {len(history.history)} 步")

			messages = self._build_messages(
				trajectory_summary, checkpoints, screenshots_dir
			)
			visual_count = sum(1 for cp in checkpoints if cp.get("is_visual_checkpoint"))
			if visual_count:
				logger.info(f"[{case_name}] 包含 {visual_count} 个视觉检查点截图")

			logger.info(f"[{case_name}] 调用评估 LLM ({Config.EVAL_LLM_MODEL})...")
			result = await self._call_llm(messages)
			logger.info(
				f"[{case_name}] 评估完成: {result.overall_status} "
				f"(pass={sum(1 for c in result.checkpoints if c.verdict == 'pass')}"
				f"/fail={sum(1 for c in result.checkpoints if c.verdict == 'fail')}"
				f"/inconclusive={sum(1 for c in result.checkpoints if c.verdict == 'inconclusive')})"
			)
			return result

		except Exception as e:
			logger.error(f"[{case_name}] 评估失败: {e}", exc_info=True)
			return EvaluationResult(
				overall_status="error",
				checkpoints=[],
				execution_errors=[f"评估服务异常: {str(e)}"],
				summary=f"评估失败: {str(e)}",
			)

	def _extract_checkpoints(self, case: dict) -> list[dict]:
		"""Extract steps that have expected_result (checkpoints to evaluate)."""
		steps_raw = case.get("steps_json", "[]")
		if isinstance(steps_raw, str):
			steps = json.loads(steps_raw)
		else:
			steps = steps_raw

		checkpoints = []
		for step in steps:
			expected = step.get("expected_result", "")
			if expected and expected.strip():
				checkpoints.append({
					"step_number": step.get("step_number", 0),
					"action_description": step.get("action_description", ""),
					"expected_result": expected.strip(),
					"is_visual_checkpoint": step.get("is_visual_checkpoint", False),
				})
		return checkpoints

	def _build_trajectory_summary(self, history: Any) -> str:
		"""Build a compact trajectory summary from agent history."""
		lines = []
		for i, item in enumerate(history.history):
			step_num = i + 1
			parts = []

			# URL
			if item.state and item.state.url:
				parts.append(f"URL: {item.state.url}")

			# Action taken
			if item.model_output:
				if item.model_output.evaluation_previous_goal:
					parts.append(f"评估: {item.model_output.evaluation_previous_goal}")
				if item.model_output.next_goal:
					parts.append(f"目标: {item.model_output.next_goal}")

			# Results
			if item.result:
				for r in item.result:
					if r.error:
						parts.append(f"错误: {r.error}")
					elif r.extracted_content:
						parts.append(f"内容: {r.extracted_content}")
					if r.is_done:
						parts.append(f"完成(success={r.success})")

			if parts:
				lines.append(f"Step {step_num}: {' | '.join(parts)}")

		# Truncate if too long
		summary = "\n".join(lines)
		if len(summary) > 3000:
			summary = summary[:3000] + "\n... (轨迹已截断)"
		return summary

	def _build_messages(
		self,
		trajectory_summary: str,
		checkpoints: list[dict],
		screenshots_dir: Path | None,
	) -> list:
		"""Build LLM messages for evaluation."""
		from browser_use.llm.messages import (
			ContentPartImageParam,
			ContentPartTextParam,
			ImageURL,
			SystemMessage,
			UserMessage,
		)

		# Format checkpoints
		checkpoint_text = "\n".join(
			f"- 步骤 {cp['step_number']}: 操作「{cp['action_description']}」→ 预期「{cp['expected_result']}」"
			+ (" [视觉检查点]" if cp.get("is_visual_checkpoint") else "")
			for cp in checkpoints
		)

		user_text = (
			f"## 需要验证的检查点\n\n{checkpoint_text}\n\n"
			f"## 执行轨迹\n\n{trajectory_summary}"
		)

		# Build user content parts
		user_content: list[ContentPartTextParam | ContentPartImageParam] = [
			ContentPartTextParam(type="text", text=user_text)
		]

		# Visual checkpoint screenshots
		if screenshots_dir and screenshots_dir.exists():
			for cp in checkpoints:
				if not cp.get("is_visual_checkpoint"):
					continue
				step_num = cp["step_number"]
				screenshot_path = screenshots_dir / f"step_{step_num}.png"
				if screenshot_path.exists():
					b64 = base64.b64encode(screenshot_path.read_bytes()).decode()
					user_content.append(ContentPartImageParam(
						image_url=ImageURL(url=f"data:image/png;base64,{b64}"),
					))
					user_content.append(ContentPartTextParam(
						type="text", text=f"[上图为步骤 {step_num} 的截图]",
					))

		messages = [
			SystemMessage(content=EVALUATION_SYSTEM_PROMPT),
			UserMessage(content=user_content),
		]
		return messages

	async def _call_llm(self, messages: list) -> EvaluationResult:
		"""Call LLM and parse structured response."""
		from browser_use.llm.openai.chat import ChatOpenAI

		llm = ChatOpenAI(
			model=Config.EVAL_LLM_MODEL,
			api_key=Config.LLM_API_KEY,
			base_url=Config.LLM_BASE_URL,
			timeout=Config.EVAL_LLM_TIMEOUT,
		)

		# Try structured output first
		try:
			logger.debug("尝试结构化输出模式...")
			response = await llm.ainvoke(messages, output_format=EvaluationResult)
			logger.debug("结构化输出解析成功")
			return response.completion
		except Exception as e:
			logger.debug(f"结构化输出失败 ({e})，回退到 JSON 手动解析")

		# Fallback: plain text response, parse JSON manually
		response = await llm.ainvoke(messages)
		content = response.completion
		if not content:
			raise ValueError("LLM returned empty response")

		logger.debug(f"LLM 原始响应长度: {len(content)} 字符")
		data = json.loads(content)
		return EvaluationResult(**data)

	def _evaluate_without_checkpoints(self, history: Any) -> EvaluationResult:
		"""When no checkpoints exist, use agent's own success verdict."""
		is_done = False
		is_successful = False

		if history.history:
			last = history.history[-1]
			if last.result:
				for r in last.result:
					if r.is_done:
						is_done = True
						is_successful = r.success or False

		logger.debug(f"Agent 自身判定: is_done={is_done}, is_successful={is_successful}")

		if is_done and is_successful:
			return EvaluationResult(
				overall_status="passed",
				checkpoints=[],
				execution_errors=[],
				summary="Agent 报告任务成功完成（无显式检查点）",
			)
		elif is_done and not is_successful:
			return EvaluationResult(
				overall_status="failed",
				checkpoints=[],
				execution_errors=[],
				summary="Agent 报告任务未成功完成",
			)
		else:
			return EvaluationResult(
				overall_status="passed",
				checkpoints=[],
				execution_errors=[],
				summary="执行完成，无检查点可评估（默认通过）",
			)


# Singleton
test_evaluation_service = TestEvaluationService()
