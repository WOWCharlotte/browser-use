"""
Test Execution Service — Parallel execution engine for automated testing.

Manages concurrent test case execution with timeout control, retry logic,
interrupt recovery, and real-time progress reporting via AG-UI events.
"""

import asyncio
import json
import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.config import Config
from app.db.database import get_db
from app.models.test_run import TestRunCreate, TestRunView, TestResultView
from app.services.execution.prompt_builder import TestPromptBuilder
from app.services.execution.runtime_state import ExecutionRuntimeState
from app.services.model_router import ModelTask, get_routed_llm
from app.services.test_case_logger import TestCaseLogger
from app.utils import uuid7str
from browser_use.llm.base import BaseChatModel

logger = logging.getLogger(__name__)

# AG-UI event type constants
EVENT_STATE_SNAPSHOT = "STATE_SNAPSHOT"
EVENT_STATE_DELTA = "STATE_DELTA"


class TestExecutionService:
	"""Parallel test execution engine."""

	def __init__(self) -> None:
		self._active_tasks: dict[str, set[asyncio.Task]] = {}
		self._active_sessions: dict[str, list] = {}  # run_id → [BrowserSession]
		self._active_loggers: dict[str, TestCaseLogger] = {}  # result_id → logger
		# result_id → Agent instance (for pause/resume)
		self._active_agents: dict[str, Any] = {}
		# result_id → BrowserSession (for live screenshot)
		self._result_sessions: dict[str, Any] = {}
		# result_id → asyncio.Event (cleared=paused, set=running)
		self._pause_events: dict[str, asyncio.Event] = {}
		# result_id → paused flag
		self._paused: dict[str, bool] = {}
		self._runtime_state = ExecutionRuntimeState()
		self._prompt_builder = TestPromptBuilder()
		self._runtime_state.active_tasks = self._active_tasks
		self._runtime_state.active_sessions = self._active_sessions
		self._runtime_state.active_loggers = self._active_loggers
		self._runtime_state.active_agents = self._active_agents
		self._runtime_state.result_sessions = self._result_sessions
		self._runtime_state.pause_events = self._pause_events
		self._runtime_state.paused = self._paused

	def _get_llm(self) -> BaseChatModel:
		"""Get routed LLM for browser test execution."""
		return get_routed_llm(ModelTask.EXECUTION)

	# ── Startup Recovery ──────────────────────────────────────────────────────

	async def recover_on_startup(self) -> None:
		"""Clean up residual running states from previous crashes."""
		db = await get_db()
		try:
			await db.execute(
				"UPDATE test_results SET status='error', error_message='服务中断恢复' "
				"WHERE status='running'"
			)
			await db.execute(
				"UPDATE test_runs SET status='aborted', completed_at=? "
				"WHERE status='running'",
				(datetime.utcnow().isoformat(),),
			)
			await db.commit()
			logger.info("recover_on_startup: cleaned residual running states")
		finally:
			await db.close()

	# ── Trajectory Cleanup ────────────────────────────────────────────────────

	async def cleanup_old_trajectories(self) -> None:
		"""Remove trajectory directories older than TRAJECTORY_RETENTION_DAYS."""
		if not Config.TRAJECTORY_DIR.exists():
			return
		cutoff = datetime.utcnow() - timedelta(days=Config.TRAJECTORY_RETENTION_DAYS)
		removed = 0
		for run_dir in Config.TRAJECTORY_DIR.iterdir():
			if not run_dir.is_dir():
				continue
			try:
				mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
				if mtime < cutoff:
					shutil.rmtree(run_dir)
					removed += 1
			except OSError as e:
				logger.warning(f"Failed to remove old trajectory dir {run_dir}: {e}")
		if removed:
			logger.info(f"cleanup_old_trajectories: removed {removed} directories")

	# ── Start Run ─────────────────────────────────────────────────────────────

	async def start_run(
		self,
		plan_id: str,
		max_concurrency: int,
		on_event: Callable[[dict[str, Any]], Awaitable[None]],
		case_ids: list[str] | None = None,
		rerun_failed: str | None = None,
		max_retries: int = 1,
		case_timeout_seconds: int = 600,
	) -> str:
		"""Start a test run. Returns the run_id."""
		max_concurrency = min(max_concurrency, Config.MAX_CONCURRENCY)
		case_timeout_seconds = max(case_timeout_seconds, 30)

		# Resolve rerun_failed to case_ids
		if rerun_failed:
			case_ids = await self._get_failed_case_ids(rerun_failed)

		# Get executable cases
		cases = await self._get_executable_cases(plan_id, case_ids)
		assert len(cases) > 0, "No executable cases found"

		# Create run record
		run_id = uuid7str()
		db = await get_db()
		try:
			await db.execute(
				"INSERT INTO test_runs (id, plan_id, status, max_concurrency, max_retries, "
				"case_timeout_seconds, case_ids_filter, rerun_of_run_id, total_cases, started_at) "
				"VALUES (?, ?, 'running', ?, ?, ?, ?, ?, ?, ?)",
				(
					run_id, plan_id, max_concurrency, max_retries,
					case_timeout_seconds,
					json.dumps(case_ids) if case_ids else None,
					rerun_failed,
					len(cases),
					datetime.utcnow().isoformat(),
				),
			)
			# Create pending result records
			for case in cases:
				result_id = uuid7str()
				case["result_id"] = result_id
				# Snapshot case content
				case_snapshot = json.dumps({
					"case_name": case["case_name"],
					"steps_json": case["steps_json"],
					"variables": case.get("variables", {}),
				}, ensure_ascii=False)
				await db.execute(
					"INSERT INTO test_results (id, run_id, case_id, variable_set_id, status, "
					"case_snapshot_json) VALUES (?, ?, ?, ?, 'pending', ?)",
					(result_id, run_id, case["case_id"], case.get("variable_set_id"), case_snapshot),
				)
			await db.commit()
		finally:
			await db.close()

		# Emit initial StateSnapshot
		case_statuses = [
			{
				"result_id": c["result_id"],
				"case_id": c["case_id"],
				"case_name": c["case_name"],
				"status": "pending",
			}
			for c in cases
		]
		await on_event({
			"type": EVENT_STATE_SNAPSHOT,
			"state": {
				"panel_mode": "execution",
				"run_progress": {
					"run_id": run_id,
					"total": len(cases),
					"completed": 0,
					"passed": 0,
					"failed": 0,
					"error": 0,
					"started_at": datetime.utcnow().isoformat(),
					"status": "running",
				},
				"case_statuses": case_statuses,
			},
		})

		# Launch execution in background
		task = asyncio.create_task(
			self._run_all_cases(run_id, cases, max_concurrency, max_retries, case_timeout_seconds, on_event)
		)
		self._active_tasks[run_id] = {task}

		return run_id

	# ── Run All Cases ─────────────────────────────────────────────────────────

	async def _run_all_cases(
		self,
		run_id: str,
		cases: list[dict],
		max_concurrency: int,
		max_retries: int,
		case_timeout_seconds: int,
		on_event: Callable[[dict[str, Any]], Awaitable[None]],
	) -> None:
		"""Execute all cases with concurrency control."""
		semaphore = asyncio.Semaphore(max_concurrency)
		completed = 0
		passed = 0
		failed = 0
		error_count = 0
		lock = asyncio.Lock()

		async def execute_one(case: dict, index: int) -> None:
			nonlocal completed, passed, failed, error_count
			async with semaphore:
				# Execute with retry (status update happens inside after resources are ready)
				result_status = await self._execute_with_retry(
					run_id, case, index, max_retries, case_timeout_seconds, on_event
				)

				# Update counters
				async with lock:
					completed += 1
					if result_status == "passed":
						passed += 1
					elif result_status == "failed":
						failed += 1
					else:
						error_count += 1

				# Emit delta
				await on_event({
					"type": EVENT_STATE_DELTA,
					"delta": [
						{"op": "replace", "path": f"/case_statuses/{index}/status", "value": result_status},
						{"op": "replace", "path": "/run_progress/completed", "value": completed},
						{"op": "replace", "path": "/run_progress/passed", "value": passed},
						{"op": "replace", "path": "/run_progress/failed", "value": failed},
						{"op": "replace", "path": "/run_progress/error", "value": error_count},
					],
				})

		try:
			tasks = set()
			for i, case in enumerate(cases):
				t = asyncio.create_task(execute_one(case, i))
				tasks.add(t)
				if run_id in self._active_tasks:
					self._active_tasks[run_id].add(t)

			await asyncio.gather(*tasks, return_exceptions=True)
		except Exception as e:
			logger.exception(f"Run {run_id} execution error: {e}")
		finally:
			# Finalize run
			db = await get_db()
			try:
				await db.execute(
					"UPDATE test_runs SET status='completed', passed_cases=?, failed_cases=?, "
					"error_cases=?, completed_at=? WHERE id=?",
					(passed, failed, error_count, datetime.utcnow().isoformat(), run_id),
				)
				await db.commit()
			finally:
				await db.close()

			# Emit completion with report URL
			await on_event({
				"type": EVENT_STATE_DELTA,
				"delta": [
					{"op": "replace", "path": "/run_progress/status", "value": "completed"},
					{"op": "add", "path": "/report_url", "value": f"/test-runs/{run_id}/report"},
					{"op": "replace", "path": "/panel_mode", "value": "report"},
				],
			})

			# Cleanup
			self._active_tasks.pop(run_id, None)
			self._active_sessions.pop(run_id, None)

	# ── Execute With Retry ────────────────────────────────────────────────────

	async def _execute_with_retry(
		self,
		run_id: str,
		case: dict,
		case_index: int,
		max_retries: int,
		case_timeout_seconds: int,
		on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
	) -> str:
		"""Execute a single case with retry on error (not on fail)."""
		result_id = case["result_id"]
		status = "error"
		retry_count = 0
		error_msg: str | None = None
		start_time = time.time()

		for attempt in range(max_retries):
			retry_count = attempt
			start_time = time.time()
			error_msg = None
			case_logger = TestCaseLogger(
				run_id=run_id,
				case_id=case["case_id"],
				set_index=case.get("set_index", 0),
			)
			# Track logger for SSE streaming
			self._active_loggers[result_id] = case_logger

			# Emit running status AFTER logger is created (so log file exists for SSE)
			if attempt == 0 and on_event and case_index >= 0:
				await on_event({
					"type": EVENT_STATE_DELTA,
					"delta": [
						{"op": "replace", "path": f"/case_statuses/{case_index}/status", "value": "running"},
					],
				})
				db = await get_db()
				try:
					await db.execute(
						"UPDATE test_results SET status='running', started_at=? WHERE id=?",
						(datetime.utcnow().isoformat(), result_id),
					)
					await db.commit()
				finally:
					await db.close()

			try:
				status = await asyncio.wait_for(
					self._execute_case_inner(run_id, case, case_logger),
					timeout=case_timeout_seconds,
				)
				if status != "error":
					break
			except asyncio.TimeoutError:
				case_logger.error(f"执行超时（{case_timeout_seconds}s）")
				status = "error"
				error_msg = f"执行超时（{case_timeout_seconds}s）"
				# Save partial trajectory before closing browser
				await self._save_trajectory_best_effort(
					self._active_agents.get(result_id), run_id, case, result_id, case_logger
				)
				# Force close browser
				await self._force_close_session(run_id, result_id)
			except asyncio.CancelledError:
				case_logger.error("执行被中止")
				status = "error"
				error_msg = "执行被中止"
				# Save partial trajectory on abort
				await self._save_trajectory_best_effort(
					self._active_agents.get(result_id), run_id, case, result_id, case_logger
				)
				break
			except Exception as e:
				case_logger.error(f"执行异常: {e}")
				status = "error"
				error_msg = str(e)
			finally:
				case_logger.close()
				self._active_loggers.pop(result_id, None)

			if status == "error" and attempt < max_retries - 1:
				case_logger_new = TestCaseLogger(run_id=run_id, case_id=case["case_id"], set_index=case.get("set_index", 0))
				case_logger_new.info(f"重试 {attempt + 2}/{max_retries}")
				case_logger_new.close()

		# Update result in DB
		duration = time.time() - start_time
		db = await get_db()
		try:
			error_message = error_msg if status == "error" else None
			await db.execute(
				"UPDATE test_results SET status=?, duration_seconds=?, retry_count=?, "
				"error_message=?, completed_at=? WHERE id=?",
				(status, duration, retry_count, error_message, datetime.utcnow().isoformat(), result_id),
			)
			await db.commit()
		finally:
			await db.close()

		return status

	# ── Execute Case Inner ────────────────────────────────────────────────────

	async def _execute_case_inner(
		self,
		run_id: str,
		case: dict,
		case_logger: TestCaseLogger,
	) -> str:
		"""
		Actual case execution logic.
		Creates browser, runs Agent, saves trajectory.
		Phase 4: evaluation is mocked (returns passed).
		"""
		from browser_use import Agent, BrowserSession

		result_id = case["result_id"]
		case_logger.info(f"开始执行用例: {case['case_name']}")

		# Register pause event for this result
		pause_event = asyncio.Event()
		pause_event.set()  # start in running state
		self._pause_events[result_id] = pause_event
		self._paused[result_id] = False

		# Create independent browser session
		from browser_use import BrowserProfile
		from app.config import Config

		# Use CDP_URL if connecting to external browser, otherwise use local browser
		if Config.CDP_URL:
			browser_profile = BrowserProfile(cdp_url=Config.CDP_URL)
		else:
			browser_profile = BrowserProfile(executable_path=Config.CHROME_EXECUTABLE_PATH) if Config.CHROME_EXECUTABLE_PATH else BrowserProfile()

		session = BrowserSession(browser_profile=browser_profile)
		if run_id not in self._active_sessions:
			self._active_sessions[run_id] = []
		self._active_sessions[run_id].append(session)
		self._result_sessions[result_id] = session

		agent: Any = None  # Track agent for trajectory saving on failure

		try:
			# Build task prompt
			task = self._build_task_prompt(case)
			case_logger.info(f"Task prompt built, start_url: {case.get('start_url', 'N/A')}")

			# Create routed LLM
			llm = self._get_llm()

			# Calculate max_steps based on case complexity
			steps_raw = case.get("steps_json", "[]")
			num_steps = len(json.loads(steps_raw) if isinstance(steps_raw, str) else steps_raw)
			max_steps = max(num_steps * 5, 25)  # At least 25, or 5x the number of steps

			# Create and run Agent
			agent = Agent(
				task=task,
				llm=llm,
				browser_session=session,
				use_vision=True,
				max_actions_per_step=1,
				max_steps=max_steps,
			)
			# Register agent for pause/resume control
			self._active_agents[result_id] = agent

			async def on_step_start(agent_instance: Agent) -> None:
				"""Check pause state before each step — blocks if paused."""
				if self._paused.get(result_id, False):
					pause_event.clear()
					case_logger.info("暂停中，等待恢复...")
					await pause_event.wait()
					case_logger.info("已恢复，继续执行")

			async def on_step_end(agent_instance: Agent) -> None:
				"""Log LLM output after each step."""
				if not agent_instance.history or not agent_instance.history.history:
					return
				last_item = agent_instance.history.history[-1]
				step_num = agent_instance.state.n_steps
				parts = []
				if last_item.model_output:
					output = last_item.model_output
					if output.evaluation_previous_goal:
						parts.append(f"上一步评估: {output.evaluation_previous_goal}")
					if output.next_goal:
						parts.append(f"下一步目标: {output.next_goal}")
					if output.thinking:
						parts.append(f"思考: {output.thinking}")
					if output.plan_update:
						parts.append(f"计划更新: {' -> '.join(output.plan_update)}")
				if last_item.result:
					for result in last_item.result:
						if result.error:
							parts.append(f"Error: {result.error}")
						elif result.extracted_content:
							parts.append(f"提取: {result.extracted_content}")
				if parts:
					case_logger.info(f"Step {step_num}: {' | '.join(parts)}")

			case_logger.info("Agent created, starting execution...")
			history = await agent.run(
				on_step_start=on_step_start,
				on_step_end=on_step_end,
			)
			case_logger.info(f"Agent execution completed, {len(history.history)} steps")

			# Save trajectory
			trajectory_dir = Config.TRAJECTORY_DIR / run_id
			trajectory_dir.mkdir(parents=True, exist_ok=True)
			trajectory_path = trajectory_dir / f"{case['case_id']}_{case.get('set_index', 0)}.json"
			history.save_to_file(str(trajectory_path))
			case_logger.info(f"Trajectory saved: {trajectory_path.name}")

			# Persist step screenshots from temp dir to trajectory dir
			screenshots_dir = trajectory_dir / f"{case['case_id']}_{case.get('set_index', 0)}_screenshots"
			screenshots_dir.mkdir(parents=True, exist_ok=True)
			for i, item in enumerate(history.history):
				src_path = item.state.screenshot_path
				if src_path and Path(src_path).exists():
					dst_path = screenshots_dir / f"step_{i + 1}.png"
					shutil.copy2(src_path, dst_path)
			persisted_count = len(list(screenshots_dir.glob("*.png")))
			case_logger.info(f"Screenshots persisted: {persisted_count} files")

			# Update trajectory path in DB
			db = await get_db()
			try:
				await db.execute(
					"UPDATE test_results SET trajectory_path=? WHERE id=?",
					(str(trajectory_path), result_id),
				)
				await db.commit()
			finally:
				await db.close()

			# Phase 5: LLM-based evaluation
			from app.services.test_evaluation_service import test_evaluation_service

			case_logger.info("开始评估...")
			eval_result = await test_evaluation_service.evaluate(
				history, case, screenshots_dir
			)
			case_logger.info(f"评估结果: {eval_result.overall_status} — {eval_result.summary}")

			# Persist evaluation to DB
			db = await get_db()
			try:
				await db.execute(
					"UPDATE test_results SET actual_result=?, evaluation=?, evaluation_details=? WHERE id=?",
					(eval_result.summary, eval_result.overall_status, eval_result.model_dump_json(), result_id),
				)
				await db.commit()
			finally:
				await db.close()

			return eval_result.overall_status

		except Exception as e:
			case_logger.error(f"执行失败: {e}")
			# Save partial trajectory even on failure
			await self._save_trajectory_best_effort(
				agent, run_id, case, result_id, case_logger
			)
			raise
		finally:
			# Close browser
			try:
				await session.close()
				case_logger.info("Browser session closed")
			except Exception as e:
				case_logger.warn(f"Browser close error: {e}")
			# Remove from active sessions
			if run_id in self._active_sessions:
				try:
					self._active_sessions[run_id].remove(session)
				except ValueError:
					pass
			# Cleanup pause/agent/session state
			self._pause_events.pop(result_id, None)
			self._paused.pop(result_id, None)
			self._active_agents.pop(result_id, None)
			self._result_sessions.pop(result_id, None)

	# ── Trajectory Save (best-effort) ────────────────────────────────────────

	async def _save_trajectory_best_effort(
		self,
		agent: Any,
		run_id: str,
		case: dict,
		result_id: str,
		case_logger: "TestCaseLogger",
	) -> None:
		"""Save whatever trajectory the agent has accumulated, even on failure."""
		if agent is None:
			return
		try:
			history = agent.history
			if not history or not history.history:
				return
			trajectory_dir = Config.TRAJECTORY_DIR / run_id
			trajectory_dir.mkdir(parents=True, exist_ok=True)
			trajectory_path = trajectory_dir / f"{case['case_id']}_{case.get('set_index', 0)}.json"
			history.save_to_file(str(trajectory_path))
			case_logger.info(f"Partial trajectory saved: {trajectory_path.name} ({len(history.history)} steps)")

			# Persist screenshots
			screenshots_dir = trajectory_dir / f"{case['case_id']}_{case.get('set_index', 0)}_screenshots"
			screenshots_dir.mkdir(parents=True, exist_ok=True)
			for i, item in enumerate(history.history):
				src_path = item.state.screenshot_path
				if src_path and Path(src_path).exists():
					dst_path = screenshots_dir / f"step_{i + 1}.png"
					shutil.copy2(src_path, dst_path)

			# Update DB
			db = await get_db()
			try:
				await db.execute(
					"UPDATE test_results SET trajectory_path=? WHERE id=?",
					(str(trajectory_path), result_id),
				)
				await db.commit()
			finally:
				await db.close()
		except Exception as save_err:
			case_logger.warn(f"Failed to save partial trajectory: {save_err}")

	# ── Build Task Prompt ─────────────────────────────────────────────────────

	def _build_task_prompt(self, case: dict) -> str:
		"""Build the Agent task prompt with variable substitution."""
		return self._prompt_builder.build(case)
		steps_raw = case.get("steps_json", "[]")
		if isinstance(steps_raw, str):
			steps = json.loads(steps_raw)
		else:
			steps = steps_raw

		variables = case.get("variables", {})
		start_url = case.get("start_url", "")

		# Variable substitution in start_url
		for var_name, var_value in variables.items():
			start_url = start_url.replace(f"{{{var_name}}}", var_value)

		parts = [f"请执行以下测试用例：{case['case_name']}"]
		parts.append(f"\n起始 URL: {start_url}")

		if variables:
			parts.append("\n测试数据:")
			for k, v in variables.items():
				parts.append(f"  - {k} = {v}")

		parts.append("\n执行步骤:")
		expected_results = []
		for step in steps:
			step_num = step.get("step_number", 0)
			action = step.get("action_description", "")
			expected = step.get("expected_result", "")
			# Variable substitution
			for var_name, var_value in variables.items():
				action = action.replace(f"{{{var_name}}}", var_value)
				if expected:
					expected = expected.replace(f"{{{var_name}}}", var_value)
			line = f"  {step_num}. {action}"
			if expected:
				line += f" → 预期: {expected}"
				expected_results.append(expected)
			parts.append(line)

		# Add explicit completion criteria
		parts.append("\n完成标准:")
		parts.append("  - 当所有步骤执行完毕后，立即调用 done 结束任务")
		parts.append("  - 如果页面上已经能观察到预期结果，即使操作方式与步骤描述略有不同，也应判定为成功并调用 done")
		parts.append("  - 不要反复尝试同一个操作超过 3 次，如果某个操作连续失败 3 次，判定为失败并调用 done")

		return "\n".join(parts)

	# ── Abort Run ─────────────────────────────────────────────────────────────

	async def abort_run(self, run_id: str) -> None:
		"""Abort a running test run."""
		# Cancel all active tasks
		tasks = self._active_tasks.get(run_id, set())
		for task in tasks:
			if not task.done():
				task.cancel()

		# Force close all active browser sessions
		sessions = self._active_sessions.get(run_id, [])
		for session in sessions:
			try:
				await session.close()
			except Exception:
				pass

		# Update DB
		db = await get_db()
		try:
			await db.execute(
				"UPDATE test_runs SET status='aborted', completed_at=? WHERE id=?",
				(datetime.utcnow().isoformat(), run_id),
			)
			await db.execute(
				"UPDATE test_results SET status='error', error_message='执行被中止' "
				"WHERE run_id=? AND status IN ('pending', 'running')",
				(run_id,),
			)
			await db.commit()
		finally:
			await db.close()

		# Cleanup
		self._active_tasks.pop(run_id, None)
		self._active_sessions.pop(run_id, None)

	# ── Retry Single Result ───────────────────────────────────────────────────

	async def retry_result(
		self,
		result_id: str,
		on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
	) -> str:
		"""Retry a single failed/error test result."""
		db = await get_db()
		try:
			async with db.execute(
				"SELECT r.*, tr.max_retries, tr.case_timeout_seconds, tr.id as run_id "
				"FROM test_results r JOIN test_runs tr ON r.run_id = tr.id WHERE r.id=?",
				(result_id,),
			) as cursor:
				row = await cursor.fetchone()
				if not row:
					raise ValueError(f"Result {result_id} not found")
				row_dict = dict(zip([d[0] for d in cursor.description], row))

			# Get case data
			async with db.execute(
				"SELECT * FROM test_cases WHERE id=?", (row_dict["case_id"],)
			) as cursor:
				case_row = await cursor.fetchone()
				if not case_row:
					raise ValueError(f"Case {row_dict['case_id']} not found")
				case_dict = dict(zip([d[0] for d in cursor.description], case_row))

			# Reset result status
			await db.execute(
				"UPDATE test_results SET status='running', error_message=NULL, "
				"retry_count=retry_count+1, started_at=? WHERE id=?",
				(datetime.utcnow().isoformat(), result_id),
			)
			await db.commit()
		finally:
			await db.close()

		# Build case execution dict
		case = {
			"result_id": result_id,
			"case_id": case_dict["id"],
			"case_name": case_dict["case_name"],
			"steps_json": case_dict["steps_json"],
			"start_url": case_dict["start_url"],
			"variables": json.loads(case_dict.get("variable_values_json") or "{}"),
			"set_index": 0,
		}

		run_id = row_dict["run_id"]
		case_timeout = row_dict["case_timeout_seconds"] or Config.CASE_TIMEOUT_SECONDS

		# Execute
		status = await self._execute_with_retry(
			run_id, case, case_index=-1, max_retries=1,
			case_timeout_seconds=case_timeout, on_event=None,
		)
		return status

	# ── Pause / Resume Single Case ────────────────────────────────────────────

	async def pause_result(self, result_id: str) -> bool:
		"""Pause a running test case. Interrupts the current LLM call."""
		agent = self._active_agents.get(result_id)
		if agent is None:
			return False
		if self._paused.get(result_id, False):
			return False  # already paused

		self._paused[result_id] = True
		# Interrupt the Agent (cancels in-flight LLM call)
		agent.pause()
		case_logger = self._active_loggers.get(result_id)
		if case_logger:
			case_logger.info("用例已暂停")
		return True

	async def resume_result(self, result_id: str) -> bool:
		"""Resume a paused test case."""
		agent = self._active_agents.get(result_id)
		if agent is None:
			return False
		if not self._paused.get(result_id, False):
			return False  # not paused

		self._paused[result_id] = False
		# Resume the Agent + unblock the step_start wait
		event = self._pause_events.get(result_id)
		if event:
			event.set()
		agent.resume()
		case_logger = self._active_loggers.get(result_id)
		if case_logger:
			case_logger.info("用例已恢复执行")
		return True

	def is_paused(self, result_id: str) -> bool:
		"""Check if a result is currently paused."""
		return self._paused.get(result_id, False)

	async def stop_result(self, result_id: str) -> bool:
		"""Stop a running or paused test case immediately.

		Calls agent.stop() to interrupt the current LLM call, closes the browser
		session, and marks the result as 'failed' with a stopped message.
		"""
		agent = self._active_agents.get(result_id)
		if agent is None:
			return False

		case_logger = self._active_loggers.get(result_id)

		# If paused, unblock first so the task can terminate
		if self._paused.get(result_id, False):
			self._paused[result_id] = False
			event = self._pause_events.get(result_id)
			if event:
				event.set()

		# Stop the agent (interrupts LLM call)
		agent.stop()

		# Close the browser session
		session = self._result_sessions.get(result_id)
		if session:
			try:
				await session.close()
			except Exception:
				pass

		# Update DB status
		db = await get_db()
		try:
			await db.execute(
				"UPDATE test_results SET status='failed', error_message='用户手动停止', "
				"completed_at=? WHERE id=?",
				(datetime.utcnow().isoformat(), result_id),
			)
			await db.commit()
		finally:
			await db.close()

		# Cleanup references
		self._active_agents.pop(result_id, None)
		self._result_sessions.pop(result_id, None)
		self._pause_events.pop(result_id, None)
		self._paused.pop(result_id, None)

		if case_logger:
			case_logger.info("用例已被手动停止")
			case_logger.close()
			self._active_loggers.pop(result_id, None)

		return True

	# ── Helper Methods ────────────────────────────────────────────────────────

	async def _get_failed_case_ids(self, run_id: str) -> list[str]:
		"""Get case_ids that failed/errored in a previous run."""
		db = await get_db()
		try:
			async with db.execute(
				"SELECT DISTINCT case_id FROM test_results WHERE run_id=? AND status IN ('failed', 'error')",
				(run_id,),
			) as cursor:
				rows = await cursor.fetchall()
				return [row[0] for row in rows]
		finally:
			await db.close()

	async def _get_executable_cases(self, plan_id: str, case_ids: list[str] | None) -> list[dict]:
		"""Get cases to execute, expanding variable sets."""
		db = await get_db()
		try:
			if case_ids:
				placeholders = ",".join("?" * len(case_ids))
				query = f"SELECT * FROM test_cases WHERE plan_id=? AND id IN ({placeholders}) ORDER BY execution_order"
				params = [plan_id] + case_ids
			else:
				query = "SELECT * FROM test_cases WHERE plan_id=? ORDER BY execution_order"
				params = [plan_id]

			async with db.execute(query, params) as cursor:
				case_rows = await cursor.fetchall()
				columns = [d[0] for d in cursor.description]

			cases = []
			for row in case_rows:
				case_dict = dict(zip(columns, row))
				# Check for variable sets
				async with db.execute(
					"SELECT * FROM test_case_variable_sets WHERE case_id=? ORDER BY set_index",
					(case_dict["id"],),
				) as cursor:
					var_rows = await cursor.fetchall()
					var_columns = [d[0] for d in cursor.description]

				if var_rows:
					# Filter out empty variable sets (all keys are empty)
					non_empty_var_rows = []
					for var_row in var_rows:
						var_dict_check = dict(zip(var_columns, var_row))
						variables_check = json.loads(var_dict_check.get("variables_json") or "{}")
						if variables_check:  # Only keep sets with actual variable values
							non_empty_var_rows.append(var_row)

					if non_empty_var_rows:
						# Expand: one execution per non-empty variable set
						for var_row in non_empty_var_rows:
							var_dict = dict(zip(var_columns, var_row))
							variables = json.loads(var_dict.get("variables_json") or "{}")
							cases.append({
								"case_id": case_dict["id"],
								"case_name": case_dict["case_name"],
								"steps_json": case_dict["steps_json"],
								"start_url": case_dict["start_url"],
								"variables": variables,
								"variable_set_id": var_dict["id"],
								"set_index": var_dict["set_index"],
							})
					else:
						# All variable sets are empty — treat as single execution
						variables = json.loads(case_dict.get("variable_values_json") or "{}")
						cases.append({
							"case_id": case_dict["id"],
							"case_name": case_dict["case_name"],
							"steps_json": case_dict["steps_json"],
							"start_url": case_dict["start_url"],
							"variables": variables,
							"variable_set_id": None,
							"set_index": 0,
						})
				else:
					# Single execution with inline variables
					variables = json.loads(case_dict.get("variable_values_json") or "{}")
					cases.append({
						"case_id": case_dict["id"],
						"case_name": case_dict["case_name"],
						"steps_json": case_dict["steps_json"],
						"start_url": case_dict["start_url"],
						"variables": variables,
						"variable_set_id": None,
						"set_index": 0,
					})

			return cases
		finally:
			await db.close()

	async def _force_close_session(self, run_id: str, result_id: str) -> None:
		"""Force close browser session for a specific result."""
		sessions = self._active_sessions.get(run_id, [])
		for session in sessions:
			try:
				await session.close()
			except Exception:
				pass

	def get_logger_for_result(self, result_id: str) -> TestCaseLogger | None:
		"""Get the active logger for a running result (for SSE streaming)."""
		return self._active_loggers.get(result_id)

	async def take_screenshot(self, result_id: str) -> str | None:
		"""Take a live screenshot of the browser for a running result. Returns base64 PNG or None."""
		import base64
		session = self._result_sessions.get(result_id)
		if session is None:
			return None
		try:
			screenshot_bytes = await session.take_screenshot()
			return base64.b64encode(screenshot_bytes).decode()
		except Exception as e:
			logger.warning(f"Failed to take screenshot for {result_id}: {e}")
			return None

	async def get_step_screenshots(self, result_id: str) -> list[dict]:
		"""Get all persisted step screenshots for a completed result.

		Returns list of {step: int, screenshot: base64_str} sorted by step number.
		Falls back to live screenshot if no persisted screenshots exist.
		"""
		import base64

		# Look up trajectory path from DB to find screenshots dir
		db = await get_db()
		try:
			async with db.execute(
				"SELECT trajectory_path FROM test_results WHERE id=?", (result_id,)
			) as cursor:
				row = await cursor.fetchone()
		finally:
			await db.close()

		if not row or not row[0]:
			# No trajectory yet — try live screenshot
			live = await self.take_screenshot(result_id)
			if live:
				return [{"step": 0, "screenshot": live}]
			return []

		trajectory_path = Path(row[0])
		screenshots_dir = trajectory_path.parent / f"{trajectory_path.stem}_screenshots"

		if not screenshots_dir.exists():
			# Fallback: read from trajectory JSON
			return self._extract_screenshots_from_trajectory(trajectory_path)

		results = []
		for png_file in sorted(screenshots_dir.glob("step_*.png")):
			step_num = int(png_file.stem.split("_")[1])
			with open(png_file, "rb") as f:
				b64 = base64.b64encode(f.read()).decode()
			results.append({"step": step_num, "screenshot": b64})

		return results

	def _extract_screenshots_from_trajectory(self, trajectory_path: Path) -> list[dict]:
		"""Extract screenshots from trajectory JSON file (fallback for older runs).

		If temp screenshots are still accessible, persists them to the screenshots
		directory so future requests don't depend on temp files.
		"""
		import base64

		if not trajectory_path.exists():
			return []

		try:
			with open(trajectory_path, "r", encoding="utf-8") as f:
				data = json.load(f)
		except Exception:
			return []

		results = []
		# Opportunistically persist to screenshots dir
		screenshots_dir = trajectory_path.parent / f"{trajectory_path.stem}_screenshots"
		should_persist = not screenshots_dir.exists()
		if should_persist:
			screenshots_dir.mkdir(parents=True, exist_ok=True)

		for i, item in enumerate(data.get("history", [])):
			state = item.get("state", {})
			screenshot_path = state.get("screenshot_path")
			if screenshot_path and Path(screenshot_path).exists():
				with open(screenshot_path, "rb") as f:
					raw = f.read()
				b64 = base64.b64encode(raw).decode()
				results.append({"step": i + 1, "screenshot": b64})
				# Persist for future access
				if should_persist:
					dst = screenshots_dir / f"step_{i + 1}.png"
					dst.write_bytes(raw)

		if should_persist and not results:
			# No screenshots found, remove empty dir
			screenshots_dir.rmdir()

		return results


# Singleton
test_execution_service = TestExecutionService()

