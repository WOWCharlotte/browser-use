"""
Tests for Test Plan Service and API.

Uses real aiosqlite with temp-file database — no mocking of DB layer.
get_db() reads DB_PATH at call time (module-level var), so patching
app.db.database.DB_PATH reliably redirects all connections to the temp db.
"""

from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio
from app.models.ingestion import TestCaseParsedSchema, TestPlanParsedSchema, TestStepSchema
from app.models.test_plan import (
	TestCaseCreate,
	TestCaseUpdate,
	TestPlanCreate,
	TestPlanUpdate,
)
from app.services.test_plan_service import TestPlanService
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def initialized_service(tmp_path):
	"""Return a TestPlanService with initialized schema."""
	db_path = str(tmp_path / "test.db")

	# Patch Config.DATABASE_PATH to use temp db
	with patch("app.db.database.DB_PATH", db_path):
		import app.db.database as db_module
		db_module.DB_PATH = db_path

		# Initialize schema
		conn = await aiosqlite.connect(db_path)
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
			CREATE TABLE IF NOT EXISTS test_replays (
				id TEXT PRIMARY KEY,
				result_id TEXT NOT NULL,
				variables_json TEXT,
				status TEXT DEFAULT 'running',
				mode TEXT DEFAULT 'hybrid',
				fallback_count INTEGER DEFAULT 0,
				trajectory_path TEXT,
				started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				completed_at DATETIME,
				FOREIGN KEY (result_id) REFERENCES test_results(id)
			);
		""")
		await conn.commit()
		await conn.close()

		svc = TestPlanService()
		yield svc


def _make_step(n: int = 1) -> TestStepSchema:
	return TestStepSchema(
		step_number=n,
		action_description=f"Step {n} action",
		expected_result=f"Step {n} expected",
		step_variables=[],
		is_visual_checkpoint=False,
	)


def _make_case_create(name: str = "Test Case") -> TestCaseCreate:
	return TestCaseCreate(
		case_name=name,
		start_url="https://example.com",
		steps=[_make_step(1), _make_step(2)],
		global_variables=[],
		variable_values={},
	)


# ── Test Plan CRUD ────────────────────────────────────────────────────────────

class TestCreatePlan:
	async def test_create_plan_returns_view(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="My Plan"))
		assert plan.id
		assert plan.name == "My Plan"
		assert plan.status == "draft"
		assert plan.max_concurrency == 3

	async def test_create_plan_with_all_fields(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(
			TestPlanCreate(
				name="Full Plan",
				description="A description",
				source_file_name="test.xlsx",
				max_concurrency=2,
			)
		)
		assert plan.description == "A description"
		assert plan.source_file_name == "test.xlsx"
		assert plan.max_concurrency == 2


class TestGetPlan:
	async def test_get_existing_plan(self, initialized_service):
		svc = initialized_service
		created = await svc.create_plan(TestPlanCreate(name="Plan A"))
		fetched = await svc.get_plan(created.id)
		assert fetched is not None
		assert fetched.id == created.id
		assert fetched.name == "Plan A"

	async def test_get_nonexistent_plan_returns_none(self, initialized_service):
		svc = initialized_service
		result = await svc.get_plan("nonexistent-id")
		assert result is None


class TestListPlans:
	async def test_list_returns_all_plans(self, initialized_service):
		svc = initialized_service
		await svc.create_plan(TestPlanCreate(name="Plan 1"))
		await svc.create_plan(TestPlanCreate(name="Plan 2"))
		plans = await svc.list_plans()
		assert len(plans) >= 2
		names = [p.name for p in plans]
		assert "Plan 1" in names
		assert "Plan 2" in names


class TestUpdatePlan:
	async def test_update_plan_name(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Old Name"))
		updated = await svc.update_plan(plan.id, TestPlanUpdate(name="New Name"))
		assert updated.name == "New Name"

	async def test_update_nonexistent_plan_raises(self, initialized_service):
		svc = initialized_service
		with pytest.raises(ValueError, match="not found"):
			await svc.update_plan("bad-id", TestPlanUpdate(name="X"))

	async def test_update_with_no_fields_returns_unchanged(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Stable"))
		result = await svc.update_plan(plan.id, TestPlanUpdate())
		assert result.name == "Stable"


class TestDeletePlan:
	async def test_delete_existing_plan(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="To Delete"))
		deleted = await svc.delete_plan(plan.id)
		assert deleted is True
		assert await svc.get_plan(plan.id) is None

	async def test_delete_nonexistent_plan_returns_false(self, initialized_service):
		svc = initialized_service
		result = await svc.delete_plan("nonexistent")
		assert result is False


class TestConfirmPlan:
	async def test_confirm_draft_plan(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Draft"))
		assert plan.status == "draft"
		confirmed = await svc.confirm_plan(plan.id)
		assert confirmed.status == "confirmed"

	async def test_confirm_nonexistent_plan_raises(self, initialized_service):
		svc = initialized_service
		with pytest.raises(ValueError, match="not found"):
			await svc.confirm_plan("bad-id")

	async def test_confirm_already_confirmed_raises(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		await svc.confirm_plan(plan.id)
		with pytest.raises(ValueError, match="not in draft"):
			await svc.confirm_plan(plan.id)


# ── Test Case CRUD ────────────────────────────────────────────────────────────

class TestCreateCase:
	async def test_create_case_under_plan(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create("Login Test"))
		assert case.id
		assert case.plan_id == plan.id
		assert case.case_name == "Login Test"
		assert len(case.steps) == 2
		assert case.status == "pending"

	async def test_create_case_nonexistent_plan_raises(self, initialized_service):
		svc = initialized_service
		with pytest.raises(ValueError, match="not found"):
			await svc.create_case("bad-plan-id", _make_case_create())

	async def test_steps_serialized_correctly(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		assert case.steps[0].step_number == 1
		assert case.steps[1].step_number == 2


class TestUpdateCase:
	async def test_update_case_name(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create("Old"))
		updated = await svc.update_case(case.id, TestCaseUpdate(case_name="New"))
		assert updated.case_name == "New"

	async def test_update_case_steps(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		new_steps = [_make_step(1), _make_step(2), _make_step(3)]
		updated = await svc.update_case(case.id, TestCaseUpdate(steps=new_steps))
		assert len(updated.steps) == 3

	async def test_update_nonexistent_case_raises(self, initialized_service):
		svc = initialized_service
		with pytest.raises(ValueError, match="not found"):
			await svc.update_case("bad-id", TestCaseUpdate(case_name="X"))


class TestDeleteCase:
	async def test_delete_existing_case(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		deleted = await svc.delete_case(case.id)
		assert deleted is True
		assert await svc.get_case(case.id) is None

	async def test_delete_nonexistent_case_returns_false(self, initialized_service):
		svc = initialized_service
		result = await svc.delete_case("nonexistent")
		assert result is False


# ── Variable Sets ─────────────────────────────────────────────────────────────

class TestVariableSets:
	async def test_create_variable_sets(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		sets = await svc.create_variable_sets(
			case.id,
			[{"username": "alice", "password": "pass1"}, {"username": "bob", "password": "pass2"}],
		)
		assert len(sets) == 2
		assert sets[0].set_index == 0
		assert sets[1].set_index == 1
		assert sets[0].variables["username"] == "alice"

	async def test_get_variable_sets_ordered(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		await svc.create_variable_sets(case.id, [{"k": "v1"}, {"k": "v2"}, {"k": "v3"}])
		sets = await svc.get_variable_sets(case.id)
		assert [s.set_index for s in sets] == [0, 1, 2]

	async def test_create_variable_sets_nonexistent_case_raises(self, initialized_service):
		svc = initialized_service
		with pytest.raises(ValueError, match="not found"):
			await svc.create_variable_sets("bad-id", [{"k": "v"}])


# ── Import Parsed Plan ────────────────────────────────────────────────────────

class TestImportParsedPlan:
	async def test_import_single_case(self, initialized_service):
		svc = initialized_service
		parsed = TestPlanParsedSchema(
			test_cases=[
				TestCaseParsedSchema(
					case_name="Login",
					start_url="https://example.com/login",
					steps=[_make_step(1)],
					global_variables=["username"],
					variable_sets=[{"username": "alice"}],
				)
			]
		)
		detail = await svc.import_parsed_plan(parsed, name="Imported Plan")
		assert detail.name == "Imported Plan"
		assert detail.status == "draft"
		assert len(detail.cases) == 1
		assert detail.cases[0].case_name == "Login"

	async def test_import_multiple_cases(self, initialized_service):
		svc = initialized_service
		parsed = TestPlanParsedSchema(
			test_cases=[
				TestCaseParsedSchema(
					case_name=f"Case {i}",
					start_url="https://example.com",
					steps=[_make_step(1)],
					global_variables=[],
					variable_sets=[{}],
				)
				for i in range(3)
			]
		)
		detail = await svc.import_parsed_plan(parsed, name="Multi Plan")
		assert len(detail.cases) == 3
		# Verify execution_order
		orders = [c.execution_order for c in detail.cases]
		assert orders == [0, 1, 2]

	async def test_import_creates_variable_sets(self, initialized_service):
		svc = initialized_service
		parsed = TestPlanParsedSchema(
			test_cases=[
				TestCaseParsedSchema(
					case_name="Parameterized",
					start_url="https://example.com",
					steps=[_make_step(1)],
					global_variables=["user"],
					variable_sets=[{"user": "alice"}, {"user": "bob"}],
				)
			]
		)
		detail = await svc.import_parsed_plan(parsed, name="Param Plan")
		case_id = detail.cases[0].id
		sets = await svc.get_variable_sets(case_id)
		assert len(sets) == 2


# ── API Endpoint Tests ────────────────────────────────────────────────────────

class TestAPIEndpoints:
	@pytest_asyncio.fixture
	async def client(self, initialized_service, tmp_path):
		"""Create test client with patched service."""
		import app.api.test_plans as tp_module
		from app import app

		# Patch the singleton in the API module
		original = tp_module.test_plan_service
		tp_module.test_plan_service = initialized_service
		try:
			async with AsyncClient(
				transport=ASGITransport(app=app), base_url="http://test"
			) as c:
				yield c
		finally:
			tp_module.test_plan_service = original

	async def test_create_plan_endpoint(self, client):
		resp = await client.post("/api/test-plans/manual", json={"name": "API Plan"})
		assert resp.status_code == 200
		data = resp.json()
		assert data["success"] is True
		assert data["data"]["name"] == "API Plan"

	async def test_list_plans_endpoint(self, client):
		await client.post("/api/test-plans/manual", json={"name": "Plan X"})
		resp = await client.get("/api/test-plans")
		assert resp.status_code == 200
		data = resp.json()
		assert data["success"] is True
		assert isinstance(data["data"], list)

	async def test_get_plan_detail_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Detail Plan"})
		plan_id = create_resp.json()["data"]["id"]
		resp = await client.get(f"/api/test-plans/{plan_id}")
		assert resp.status_code == 200
		data = resp.json()
		assert data["data"]["id"] == plan_id
		assert "cases" in data["data"]

	async def test_get_nonexistent_plan_returns_404(self, client):
		resp = await client.get("/api/test-plans/nonexistent-id")
		assert resp.status_code == 404
		assert resp.json()["success"] is False

	async def test_update_plan_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Old"})
		plan_id = create_resp.json()["data"]["id"]
		resp = await client.put(f"/api/test-plans/{plan_id}", json={"name": "New"})
		assert resp.status_code == 200
		assert resp.json()["data"]["name"] == "New"

	async def test_delete_plan_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Delete Me"})
		plan_id = create_resp.json()["data"]["id"]
		resp = await client.delete(f"/api/test-plans/{plan_id}")
		assert resp.status_code == 200
		assert resp.json()["success"] is True
		# Verify gone
		get_resp = await client.get(f"/api/test-plans/{plan_id}")
		assert get_resp.status_code == 404

	async def test_confirm_plan_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Confirm Me"})
		plan_id = create_resp.json()["data"]["id"]
		resp = await client.put(f"/api/test-plans/{plan_id}/confirm")
		assert resp.status_code == 200
		assert resp.json()["data"]["status"] == "confirmed"

	async def test_add_case_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Plan"})
		plan_id = create_resp.json()["data"]["id"]
		case_data = {
			"case_name": "Login Test",
			"start_url": "https://example.com",
			"steps": [
				{
					"step_number": 1,
					"action_description": "Click login",
					"expected_result": "Login page shown",
					"step_variables": [],
					"is_visual_checkpoint": False,
				}
			],
			"global_variables": [],
			"variable_values": {},
		}
		resp = await client.post(f"/api/test-plans/{plan_id}/cases", json=case_data)
		assert resp.status_code == 200
		assert resp.json()["data"]["case_name"] == "Login Test"

	async def test_import_variable_sets_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Plan"})
		plan_id = create_resp.json()["data"]["id"]
		case_data = {
			"case_name": "Param Test",
			"start_url": "https://example.com",
			"steps": [
				{
					"step_number": 1,
					"action_description": "Login as {user}",
					"step_variables": ["user"],
					"is_visual_checkpoint": False,
				}
			],
			"global_variables": ["user"],
			"variable_values": {},
		}
		case_resp = await client.post(f"/api/test-plans/{plan_id}/cases", json=case_data)
		case_id = case_resp.json()["data"]["id"]

		import_resp = await client.post(
			f"/api/test-cases/{case_id}/variables/import",
			json={"variable_sets": [{"user": "alice"}, {"user": "bob"}]},
		)
		assert import_resp.status_code == 200
		assert len(import_resp.json()["data"]) == 2

	async def test_get_variable_sets_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Plan"})
		plan_id = create_resp.json()["data"]["id"]
		case_data = {
			"case_name": "Test",
			"start_url": "https://example.com",
			"steps": [
				{
					"step_number": 1,
					"action_description": "Do something",
					"step_variables": [],
					"is_visual_checkpoint": False,
				}
			],
			"global_variables": [],
			"variable_values": {},
		}
		case_resp = await client.post(f"/api/test-plans/{plan_id}/cases", json=case_data)
		case_id = case_resp.json()["data"]["id"]
		await client.post(
			f"/api/test-cases/{case_id}/variables/import",
			json={"variable_sets": [{"k": "v"}]},
		)
		resp = await client.get(f"/api/test-cases/{case_id}/variables")
		assert resp.status_code == 200
		assert len(resp.json()["data"]) == 1

	async def test_update_case_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Plan"})
		plan_id = create_resp.json()["data"]["id"]
		case_data = {
			"case_name": "Old Case",
			"start_url": "https://example.com",
			"steps": [{"step_number": 1, "action_description": "Do it", "step_variables": [], "is_visual_checkpoint": False}],
			"global_variables": [],
			"variable_values": {},
		}
		case_resp = await client.post(f"/api/test-plans/{plan_id}/cases", json=case_data)
		case_id = case_resp.json()["data"]["id"]
		resp = await client.put(f"/api/test-cases/{case_id}", json={"case_name": "New Case"})
		assert resp.status_code == 200
		assert resp.json()["data"]["case_name"] == "New Case"

	async def test_delete_case_endpoint(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Plan"})
		plan_id = create_resp.json()["data"]["id"]
		case_data = {
			"case_name": "Delete Me",
			"start_url": "https://example.com",
			"steps": [{"step_number": 1, "action_description": "Do it", "step_variables": [], "is_visual_checkpoint": False}],
			"global_variables": [],
			"variable_values": {},
		}
		case_resp = await client.post(f"/api/test-plans/{plan_id}/cases", json=case_data)
		case_id = case_resp.json()["data"]["id"]
		resp = await client.delete(f"/api/test-cases/{case_id}")
		assert resp.status_code == 200
		assert resp.json()["success"] is True

	async def test_confirm_plan_already_confirmed_returns_400(self, client):
		create_resp = await client.post("/api/test-plans/manual", json={"name": "Plan"})
		plan_id = create_resp.json()["data"]["id"]
		await client.put(f"/api/test-plans/{plan_id}/confirm")
		resp = await client.put(f"/api/test-plans/{plan_id}/confirm")
		assert resp.status_code == 400
		assert resp.json()["success"] is False


# ── Additional Service Tests ──────────────────────────────────────────────────

class TestGetCase:
	async def test_get_case_by_id(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create("My Case"))
		fetched = await svc.get_case(case.id)
		assert fetched is not None
		assert fetched.id == case.id
		assert fetched.case_name == "My Case"

	async def test_get_nonexistent_case_returns_none(self, initialized_service):
		svc = initialized_service
		result = await svc.get_case("nonexistent-id")
		assert result is None


class TestListCases:
	async def test_list_cases_empty(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		cases = await svc.list_cases(plan.id)
		assert cases == []

	async def test_list_cases_ordered_by_execution_order(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		# Create cases with explicit execution_order
		c2 = TestCaseCreate(
			case_name="Case 2", start_url="https://example.com",
			steps=[_make_step(1)], global_variables=[], variable_values={},
			execution_order=2,
		)
		c1 = TestCaseCreate(
			case_name="Case 1", start_url="https://example.com",
			steps=[_make_step(1)], global_variables=[], variable_values={},
			execution_order=1,
		)
		await svc.create_case(plan.id, c2)
		await svc.create_case(plan.id, c1)
		cases = await svc.list_cases(plan.id)
		assert cases[0].case_name == "Case 1"
		assert cases[1].case_name == "Case 2"


class TestDeletePlanCascade:
	async def test_delete_plan_cascades_to_cases(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		await svc.delete_plan(plan.id)
		# Case should also be gone
		assert await svc.get_case(case.id) is None

	async def test_delete_plan_cascades_to_variable_sets(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		await svc.create_variable_sets(case.id, [{"k": "v"}])
		await svc.delete_plan(plan.id)
		# Variable sets should also be gone
		sets = await svc.get_variable_sets(case.id)
		assert sets == []


class TestEdgeCases:
	async def test_list_plans_empty(self, initialized_service):
		svc = initialized_service
		plans = await svc.list_plans()
		assert plans == []

	async def test_create_variable_sets_empty_list(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		sets = await svc.create_variable_sets(case.id, [])
		assert sets == []

	async def test_get_variable_sets_empty(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		sets = await svc.get_variable_sets(case.id)
		assert sets == []

	async def test_import_parsed_plan_empty_cases(self, initialized_service):
		svc = initialized_service
		parsed = TestPlanParsedSchema(test_cases=[])
		detail = await svc.import_parsed_plan(parsed, name="Empty Plan")
		assert detail.name == "Empty Plan"
		assert detail.cases == []

	async def test_get_plan_detail_nonexistent_returns_none(self, initialized_service):
		svc = initialized_service
		result = await svc.get_plan_detail("nonexistent-id")
		assert result is None

	async def test_update_case_variable_values(self, initialized_service):
		svc = initialized_service
		plan = await svc.create_plan(TestPlanCreate(name="Plan"))
		case = await svc.create_case(plan.id, _make_case_create())
		updated = await svc.update_case(case.id, TestCaseUpdate(variable_values={"user": "alice"}))
		assert updated.variable_values == {"user": "alice"}

	async def test_max_concurrency_boundary_values(self, initialized_service):
		from pydantic import ValidationError
		svc = initialized_service
		# min boundary
		plan = await svc.create_plan(TestPlanCreate(name="Plan", max_concurrency=1))
		assert plan.max_concurrency == 1
		# max boundary
		plan2 = await svc.create_plan(TestPlanCreate(name="Plan2", max_concurrency=5))
		assert plan2.max_concurrency == 5
		# out of range
		with pytest.raises(ValidationError):
			TestPlanCreate(name="Bad", max_concurrency=6)
