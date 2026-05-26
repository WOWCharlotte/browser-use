"""
Test Replay Service — Replays recorded test trajectories via browser-use Agent.rerun_history().

Supports hybrid mode: deterministic replay with AI fallback on element-matching failures.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from app.config import Config
from app.db.database import get_db
from app.utils import uuid7str

logger = logging.getLogger(__name__)


class TestReplayService:
	"""Manages test replay lifecycle: launch, execute, and query."""

	def __init__(self) -> None:
		self._active_tasks: dict[str, asyncio.Task] = {}

	async def replay(self, result_id: str, new_variables: dict[str, str] | None = None) -> str:
		"""Start a replay for a given test result. Returns replay_id immediately."""
		db = await get_db()
		try:
			# Load original result record
			async with db.execute(
				"SELECT trajectory_path, case_snapshot_json FROM test_results WHERE id=?",
				(result_id,),
			) as cursor:
				row = await cursor.fetchone()
			if not row:
				raise ValueError(f"Test result {result_id} not found")

			trajectory_path = row[0]
			case_snapshot_json = row[1]

			if not trajectory_path or not Path(trajectory_path).exists():
				raise ValueError(f"Trajectory file not found for result {result_id}")

			case_snapshot = json.loads(case_snapshot_json) if case_snapshot_json else {}

			# Create replay record
			replay_id = uuid7str()
			now = datetime.utcnow().isoformat()
			await db.execute(
				"INSERT INTO test_replays "
				"(id, result_id, variables_json, status, mode, fallback_count, started_at) "
				"VALUES (?, ?, ?, 'running', 'hybrid', 0, ?)",
				(
					replay_id,
					result_id,
					json.dumps(new_variables, ensure_ascii=False) if new_variables else None,
					now,
				),
			)
			await db.commit()
		finally:
			await db.close()

		# Launch background execution
		task = asyncio.create_task(
			self._run_replay(replay_id, result_id, trajectory_path, case_snapshot, new_variables)
		)
		self._active_tasks[replay_id] = task
		task.add_done_callback(lambda t: self._active_tasks.pop(replay_id, None))

		return replay_id

	async def _run_replay(
		self,
		replay_id: str,
		result_id: str,
		trajectory_path: str,
		case_snapshot: dict,
		new_variables: dict[str, str] | None,
	) -> None:
		"""Background task: execute the replay and persist results."""
		from browser_use import Agent, BrowserSession
		from browser_use.agent.views import AgentHistoryList
		from browser_use.llm.openai.chat import ChatOpenAI

		session: BrowserSession | None = None
		fallback_count = 0

		try:
			# Build LLM (used as ai_step_llm for fallback)
			llm = ChatOpenAI(
				model=Config.LLM_MODEL,
				api_key=Config.LLM_API_KEY,
				base_url=Config.LLM_BASE_URL,
			)

			# Build task prompt from case snapshot
			task = self._build_task_prompt(case_snapshot, new_variables)

			# Create browser session and agent
			from browser_use import BrowserProfile
			from app.config import Config
			browser_profile = BrowserProfile(executable_path=Config.CHROME_EXECUTABLE_PATH) if Config.CHROME_EXECUTABLE_PATH else BrowserProfile()
			session = BrowserSession(browser_profile=browser_profile)
			agent = Agent(
				task=task,
				llm=llm,
				browser_session=session,
				use_vision=True,
			)

			# Load history from trajectory file
			history = AgentHistoryList.load_from_file(trajectory_path, agent.AgentOutput)

			# Execute replay with AI fallback enabled
			results = await agent.rerun_history(
				history,
				max_retries=3,
				skip_failures=True,
				delay_between_actions=2.0,
				ai_step_llm=llm,
			)

			# Count fallback invocations (steps that had errors then succeeded via AI)
			fallback_count = sum(
				1 for r in results
				if r.error and "AI step" in (r.error or "")
			)

			# Determine final status
			errors = [r for r in results if r.error and "Skipped" not in (r.error or "")]
			status = "passed" if not errors else "failed"

			# Save replay trajectory
			replay_trajectory_dir = Config.TRAJECTORY_DIR / "replays"
			replay_trajectory_dir.mkdir(parents=True, exist_ok=True)
			replay_trajectory_path = replay_trajectory_dir / f"{replay_id}.json"
			agent.history.save_to_file(str(replay_trajectory_path))

			# Update DB record
			await self._update_replay_record(
				replay_id,
				status=status,
				fallback_count=fallback_count,
				trajectory_path=str(replay_trajectory_path),
			)

		except Exception as e:
			logger.exception(f"Replay {replay_id} failed: {e}")
			await self._update_replay_record(
				replay_id,
				status="error",
				fallback_count=fallback_count,
				trajectory_path=None,
			)
		finally:
			if session:
				try:
					await session.close()
				except Exception as e:
					logger.warning(f"Failed to close browser session for replay {replay_id}: {e}")

	async def _update_replay_record(
		self,
		replay_id: str,
		status: str,
		fallback_count: int,
		trajectory_path: str | None,
	) -> None:
		"""Persist final replay state to the database."""
		db = await get_db()
		try:
			await db.execute(
				"UPDATE test_replays SET status=?, fallback_count=?, trajectory_path=?, "
				"completed_at=? WHERE id=?",
				(status, fallback_count, trajectory_path, datetime.utcnow().isoformat(), replay_id),
			)
			await db.commit()
		finally:
			await db.close()

	def _build_task_prompt(
		self,
		case_snapshot: dict,
		new_variables: dict[str, str] | None,
	) -> str:
		"""Build the Agent task prompt from case snapshot, substituting variables."""
		case_name = case_snapshot.get("case_name", "未命名用例")
		steps_raw = case_snapshot.get("steps_json", "[]")
		if isinstance(steps_raw, str):
			steps = json.loads(steps_raw)
		else:
			steps = steps_raw

		# Merge variables: original from snapshot, overridden by new_variables
		variables: dict[str, str] = case_snapshot.get("variables", {}) or {}
		if new_variables:
			variables = {**variables, **new_variables}

		start_url = case_snapshot.get("start_url", "")
		for var_name, var_value in variables.items():
			start_url = start_url.replace(f"{{{var_name}}}", var_value)

		parts = [f"请执行以下测试用例：{case_name}"]
		parts.append(f"\n起始 URL: {start_url}")

		if variables:
			parts.append("\n测试数据:")
			for k, v in variables.items():
				parts.append(f"  - {k} = {v}")

		parts.append("\n执行步骤:")
		for step in steps:
			step_num = step.get("step_number", 0)
			action = step.get("action_description", "")
			expected = step.get("expected_result", "")
			for var_name, var_value in variables.items():
				action = action.replace(f"{{{var_name}}}", var_value)
				if expected:
					expected = expected.replace(f"{{{var_name}}}", var_value)
			line = f"  {step_num}. {action}"
			if expected:
				line += f" → 预期: {expected}"
			parts.append(line)

		parts.append("\n完成标准:")
		parts.append("  - 当所有步骤执行完毕后，立即调用 done 结束任务")
		parts.append("  - 如果页面上已经能观察到预期结果，即使操作方式与步骤描述略有不同，也应判定为成功并调用 done")
		parts.append("  - 不要反复尝试同一个操作超过 3 次，如果某个操作连续失败 3 次，判定为失败并调用 done")

		return "\n".join(parts)

	async def get_replay(self, replay_id: str) -> dict | None:
		"""Fetch a single replay record by ID."""
		db = await get_db()
		try:
			async with db.execute(
				"SELECT id, result_id, variables_json, status, mode, fallback_count, "
				"trajectory_path, started_at, completed_at FROM test_replays WHERE id=?",
				(replay_id,),
			) as cursor:
				row = await cursor.fetchone()
				if not row:
					return None
				columns = [d[0] for d in cursor.description]
				return dict(zip(columns, row))
		finally:
			await db.close()


# Singleton
test_replay_service = TestReplayService()
