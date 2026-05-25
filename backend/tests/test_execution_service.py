"""
Tests for Test Execution Service and API.

Uses real aiosqlite with temp-file database.
Mocks browser_use Agent/BrowserSession since we can't run real browsers in tests.
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.services.test_case_logger import TestCaseLogger
from app.services.test_execution_service import TestExecutionService


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_path(tmp_path):
	"""Create a temp database with full schema."""
	db_file = str(tmp_path / "test_exec.db")

	conn = await aiosqlite.connect(db_file)
	conn.row_factory = aiosqlite.Row
	await conn.executescript("""
		CREATE TABLE IF NOT EXISTS test_plans (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			description TEXT,
			source_file_name TEXT,
			max_concurrency INTEGER DEFAULT 3,
			status TEXT DEFAULT 'draft',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE TABLE IF NOT EXISTS test_cases (
			id TEXT PRIMARY KEY,
			plan_id TEXT NOT NULL,
			case_name TEXT NOT NULL,
			description TEXT,
			module TEXT,
			function_point TEXT,
			start_url TEXT NOT NULL,
			steps_json TEXT NOT NULL,
			global_variables TEXT,
			variable_values_json TEXT,
			status TEXT DEFAULT 'pending',
			execution_order INTEGER,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (plan_id) REFERENCES test_plans(id) ON DELETE CASCADE
		);
		CREATE TABLE IF NOT EXISTS test_case_variable_sets (
			id TEXT PRIMARY KEY,
			case_id TEXT NOT NULL,
			set_index INTEGER NOT NULL,
			variables_json TEXT NOT NULL,
			status TEXT DEFAULT 'pending',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE
		);
		CREATE TABLE IF NOT EXISTS test_runs (
			id TEXT PRIMARY KEY,
			plan_id TEXT NOT NULL,
			status TEXT DEFAULT 'running',
			max_concurrency INTEGER DEFAULT 3,
			max_retries INTEGER DEFAULT 1,
			case_timeout_seconds INTEGER DEFAULT 600,
			case_ids_filter TEXT,
			rerun_of_run_id TEXT,
			total_cases INTEGER DEFAULT 0,
			passed_cases INTEGER DEFAULT 0,
			failed_cases INTEGER DEFAULT 0,
			error_cases INTEGER DEFAULT 0,
			started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			completed_at DATETIME,
			FOREIGN KEY (plan_id) REFERENCES test_plans(id)
		);
		CREATE TABLE IF NOT EXISTS test_results (
			id TEXT PRIMARY KEY,
			run_id TEXT NOT NULL,
			case_id TEXT NOT NULL,
			variable_set_id TEXT,
			session_id TEXT,
			status TEXT DEFAULT 'pending',
			actual_result TEXT,
			evaluation TEXT,
			evaluation_details TEXT,
			error_message TEXT,
			duration_seconds REAL,
			retry_count INTEGER DEFAULT 0,
			case_snapshot_json TEXT,
			original_status TEXT,
			override_reason TEXT,
			trajectory_path TEXT,
			started_at DATETIME,
			completed_at DATETIME,
			FOREIGN KEY (run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
			FOREIGN KEY (case_id) REFERENCES test_cases(id)
		);
	""")
	await conn.commit()
	await conn.close()

	with patch("app.db.database.DB_PATH", db_file):
		import app.db.database as db_module
		db_module.DB_PATH = db_file
		yield db_file


@pytest_asyncio.fixture
async def seeded_db(db_path):
	"""Seed the database with a confirmed plan and test cases."""
	conn = await aiosqlite.connect(db_path)
	conn.row_factory = aiosqlite.Row

	plan_id = "plan-001"
	await conn.execute(
		"INSERT INTO test_plans (id, name, status) VALUES (?, ?, 'confirmed')",
		(plan_id, "Test Plan Alpha"),
	)

	steps = json.dumps([
		{"step_number": 1, "action_description": "打开首页", "expected_result": "页面加载成功", "step_variables": [], "is_visual_checkpoint": False},
		{"step_number": 2, "action_description": "点击登录", "expected_result": None, "step_variables": [], "is_visual_checkpoint": False},
	])

	for i in range(3):
		case_id = f"case-{i:03d}"
		await conn.execute(
			"INSERT INTO test_cases (id, plan_id, case_name, start_url, steps_json, execution_order) "
			"VALUES (?, ?, ?, ?, ?, ?)",
			(case_id, plan_id, f"用例 {i+1}", "http://localhost:8080", steps, i),
		)

	await conn.commit()
	await conn.close()
	return plan_id


# ── TestCaseLogger Tests ──────────────────────────────────────────────────────


class TestTestCaseLogger:
	def test_creates_log_file(self, tmp_path):
		with patch.object(Path, "parent", new_callable=lambda: property(lambda self: tmp_path)):
			pass
		# Use Config patch
		with patch("app.services.test_case_logger.Config") as mock_config:
			mock_config.TRAJECTORY_DIR = tmp_path
			logger = TestCaseLogger(run_id="run-1", case_id="case-1", set_index=0)
			logger.info("test message")
			logger.close()

			log_file = tmp_path / "run-1" / "case-1_0.log"
			assert log_file.exists()
			content = log_file.read_text(encoding="utf-8")
			assert "[INFO]" in content
			assert "test message" in content

	def test_log_levels(self, tmp_path):
		with patch("app.services.test_case_logger.Config") as mock_config:
			mock_config.TRAJECTORY_DIR = tmp_path
			logger = TestCaseLogger(run_id="run-2", case_id="case-2", set_index=1)
			logger.info("info msg")
			logger.warn("warn msg")
			logger.error("error msg")
			logger.close()

			log_file = tmp_path / "run-2" / "case-2_1.log"
			content = log_file.read_text(encoding="utf-8")
			assert "[INFO]" in content
			assert "[WARNING]" in content
			assert "[ERROR]" in content

	def test_close_prevents_further_writes(self, tmp_path):
		with patch("app.services.test_case_logger.Config") as mock_config:
			mock_config.TRAJECTORY_DIR = tmp_path
			logger = TestCaseLogger(run_id="run-3", case_id="case-3", set_index=0)
			logger.info("before close")
			logger.close()
			# After close, handler is removed — no crash, just no-op
			logger.info("after close")


# ── TestExecutionService Tests ────────────────────────────────────────────────


class TestExecutionServiceRecovery:
	async def test_recover_on_startup_cleans_running_results(self, seeded_db, db_path):
		"""Running results should be marked as error on startup."""
		# Insert a running result
		conn = await aiosqlite.connect(db_path)
		await conn.execute(
			"INSERT INTO test_runs (id, plan_id, status) VALUES ('run-orphan', 'plan-001', 'running')"
		)
		await conn.execute(
			"INSERT INTO test_results (id, run_id, case_id, status) VALUES ('res-orphan', 'run-orphan', 'case-000', 'running')"
		)
		await conn.commit()
		await conn.close()

		service = TestExecutionService()
		await service.recover_on_startup()

		conn = await aiosqlite.connect(db_path)
		conn.row_factory = aiosqlite.Row
		async with conn.execute("SELECT status FROM test_results WHERE id='res-orphan'") as cur:
			row = await cur.fetchone()
			assert row[0] == "error"
		async with conn.execute("SELECT status FROM test_runs WHERE id='run-orphan'") as cur:
			row = await cur.fetchone()
			assert row[0] == "aborted"
		await conn.close()


class TestExecutionServiceGetCases:
	async def test_get_executable_cases_all(self, seeded_db, db_path):
		service = TestExecutionService()
		cases = await service._get_executable_cases("plan-001", None)
		assert len(cases) == 3
		assert all(c["case_name"].startswith("用例") for c in cases)

	async def test_get_executable_cases_filtered(self, seeded_db, db_path):
		service = TestExecutionService()
		cases = await service._get_executable_cases("plan-001", ["case-000", "case-002"])
		assert len(cases) == 2
		case_ids = [c["case_id"] for c in cases]
		assert "case-000" in case_ids
		assert "case-002" in case_ids


class TestExecutionServiceBuildPrompt:
	def test_build_task_prompt_basic(self):
		service = TestExecutionService()
		case = {
			"case_name": "登录测试",
			"start_url": "http://localhost:8080",
			"steps_json": json.dumps([
				{"step_number": 1, "action_description": "输入用户名 {username}", "expected_result": "输入成功", "step_variables": ["username"], "is_visual_checkpoint": False},
			]),
			"variables": {"username": "admin"},
		}
		prompt = service._build_task_prompt(case)
		assert "登录测试" in prompt
		assert "admin" in prompt
		assert "{username}" not in prompt  # Variable should be replaced

	def test_build_task_prompt_no_variables(self):
		service = TestExecutionService()
		case = {
			"case_name": "简单测试",
			"start_url": "http://example.com",
			"steps_json": json.dumps([
				{"step_number": 1, "action_description": "点击按钮", "expected_result": None, "step_variables": [], "is_visual_checkpoint": False},
			]),
			"variables": {},
		}
		prompt = service._build_task_prompt(case)
		assert "简单测试" in prompt
		assert "点击按钮" in prompt


class TestExecutionServiceStartRun:
	async def test_start_run_creates_records(self, seeded_db, db_path, tmp_path):
		"""start_run should create run + result records and emit StateSnapshot."""
		events = []

		async def on_event(event):
			events.append(event)

		service = TestExecutionService()

		# Mock the actual execution to avoid needing browser_use
		with patch.object(service, "_run_all_cases", new_callable=AsyncMock):
			with patch("app.services.test_execution_service.Config") as mock_config:
				mock_config.MAX_CONCURRENCY = 5
				mock_config.TRAJECTORY_DIR = tmp_path
				run_id = await service.start_run(
					plan_id="plan-001",
					max_concurrency=2,
					on_event=on_event,
				)

		assert run_id is not None

		# Verify StateSnapshot was emitted
		snapshot_events = [e for e in events if e.get("type") == "STATE_SNAPSHOT"]
		assert len(snapshot_events) == 1
		state = snapshot_events[0]["state"]
		assert state["panel_mode"] == "execution"
		assert state["run_progress"]["total"] == 3
		assert len(state["case_statuses"]) == 3

		# Verify DB records
		conn = await aiosqlite.connect(db_path)
		conn.row_factory = aiosqlite.Row
		async with conn.execute("SELECT * FROM test_runs WHERE id=?", (run_id,)) as cur:
			row = await cur.fetchone()
			assert row is not None
			assert dict(row)["status"] == "running"
			assert dict(row)["total_cases"] == 3
		async with conn.execute("SELECT COUNT(*) FROM test_results WHERE run_id=?", (run_id,)) as cur:
			row = await cur.fetchone()
			assert row[0] == 3
		await conn.close()


class TestExecutionServiceAbort:
	async def test_abort_run_marks_aborted(self, seeded_db, db_path):
		"""abort_run should mark run as aborted and pending results as error."""
		# Create a run with pending results
		conn = await aiosqlite.connect(db_path)
		await conn.execute(
			"INSERT INTO test_runs (id, plan_id, status, total_cases) VALUES ('run-abort', 'plan-001', 'running', 3)"
		)
		await conn.execute(
			"INSERT INTO test_results (id, run_id, case_id, status) VALUES ('res-1', 'run-abort', 'case-000', 'pending')"
		)
		await conn.execute(
			"INSERT INTO test_results (id, run_id, case_id, status) VALUES ('res-2', 'run-abort', 'case-001', 'running')"
		)
		await conn.execute(
			"INSERT INTO test_results (id, run_id, case_id, status) VALUES ('res-3', 'run-abort', 'case-002', 'passed')"
		)
		await conn.commit()
		await conn.close()

		service = TestExecutionService()
		await service.abort_run("run-abort")

		conn = await aiosqlite.connect(db_path)
		conn.row_factory = aiosqlite.Row
		async with conn.execute("SELECT status FROM test_runs WHERE id='run-abort'") as cur:
			row = await cur.fetchone()
			assert row[0] == "aborted"
		# pending and running should be error, passed should remain
		async with conn.execute("SELECT id, status FROM test_results WHERE run_id='run-abort' ORDER BY id") as cur:
			rows = await cur.fetchall()
			statuses = {row[0]: row[1] for row in rows}
			assert statuses["res-1"] == "error"
			assert statuses["res-2"] == "error"
			assert statuses["res-3"] == "passed"
		await conn.close()


# ── API Tests ─────────────────────────────────────────────────────────────────


class TestTestRunsAPI:
	@pytest_asyncio.fixture
	async def client(self, seeded_db, db_path):
		"""Create test client with patched DB."""
		with patch("app.db.database.DB_PATH", db_path):
			import app.db.database as db_module
			db_module.DB_PATH = db_path
			from app import app as fastapi_app
			transport = ASGITransport(app=fastapi_app)
			async with AsyncClient(transport=transport, base_url="http://test") as c:
				yield c

	async def test_get_run_not_found(self, client):
		resp = await client.get("/api/test-runs/nonexistent")
		assert resp.status_code == 404
		data = resp.json()
		assert data["success"] is False
		assert data["code"] == "NOT_FOUND"

	async def test_abort_not_found(self, client):
		resp = await client.post("/api/test-runs/nonexistent/abort")
		assert resp.status_code == 404
		data = resp.json()
		assert data["success"] is False
		assert data["code"] == "NOT_FOUND"

	async def test_override_result(self, client, db_path):
		# Insert a result to override
		conn = await aiosqlite.connect(db_path)
		await conn.execute(
			"INSERT INTO test_runs (id, plan_id, status) VALUES ('run-ov', 'plan-001', 'completed')"
		)
		await conn.execute(
			"INSERT INTO test_results (id, run_id, case_id, status) VALUES ('res-ov', 'run-ov', 'case-000', 'failed')"
		)
		await conn.commit()
		await conn.close()

		resp = await client.put(
			"/api/test-results/res-ov/override",
			json={"status": "passed", "reason": "人工确认通过"},
		)
		assert resp.status_code == 200
		data = resp.json()
		assert data["success"] is True
		assert data["data"]["status"] == "passed"
		assert data["data"]["original_status"] == "failed"

	async def test_get_logs_not_found(self, client):
		resp = await client.get("/api/test-results/nonexistent/logs")
		assert resp.status_code == 404
		data = resp.json()
		assert data["success"] is False

	async def test_retry_invalid_state(self, client, db_path):
		# Insert a passed result — should not be retryable
		conn = await aiosqlite.connect(db_path)
		await conn.execute(
			"INSERT INTO test_runs (id, plan_id, status) VALUES ('run-rt', 'plan-001', 'completed')"
		)
		await conn.execute(
			"INSERT INTO test_results (id, run_id, case_id, status) VALUES ('res-rt', 'run-rt', 'case-000', 'passed')"
		)
		await conn.commit()
		await conn.close()

		resp = await client.post("/api/test-results/res-rt/retry")
		assert resp.status_code == 400
		data = resp.json()
		assert data["success"] is False
		assert data["code"] == "INVALID_STATE"
