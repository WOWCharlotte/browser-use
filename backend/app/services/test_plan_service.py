"""
Test Plan Service.

Provides CRUD operations for test plans, test cases, and variable sets.
"""

import json
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.ingestion import TestPlanParsedSchema
from app.models.test_plan import (
	TestCaseCreate,
	TestCaseUpdate,
	TestCaseView,
	TestPlanCreate,
	TestPlanDetailView,
	TestPlanUpdate,
	TestPlanView,
	VariableSetView,
)
from app.utils import uuid7str

logger = logging.getLogger(__name__)

# Explicit field whitelists to prevent SQL injection via dynamic column names
_PLAN_UPDATE_FIELDS: frozenset[str] = frozenset({"name", "description", "max_concurrency"})
_CASE_UPDATE_FIELDS: frozenset[str] = frozenset({
	"case_name", "description", "module", "function_point",
	"start_url", "steps_json", "global_variables", "variable_values_json", "execution_order",
})


def _row_to_dict(row) -> dict:
	"""Convert aiosqlite.Row to dict."""
	return dict(zip(row.keys(), row))


def _parse_case_row(row: dict) -> TestCaseView:
	"""Parse a database row into a TestCaseView."""
	from app.models.ingestion import TestStepSchema

	try:
		steps_raw = row.get("steps_json") or "[]"
		steps_data = json.loads(steps_raw)
		steps = [TestStepSchema(**s) for s in steps_data]
	except (json.JSONDecodeError, Exception) as e:
		logger.error(f"Failed to parse steps_json for case {row.get('id')}: {e}")
		steps = []

	try:
		global_vars_raw = row.get("global_variables") or "[]"
		global_variables = json.loads(global_vars_raw)
	except json.JSONDecodeError as e:
		logger.error(f"Failed to parse global_variables for case {row.get('id')}: {e}")
		global_variables = []

	try:
		variable_values_raw = row.get("variable_values_json") or "{}"
		variable_values = json.loads(variable_values_raw)
	except json.JSONDecodeError as e:
		logger.error(f"Failed to parse variable_values_json for case {row.get('id')}: {e}")
		variable_values = {}

	return TestCaseView(
		id=row["id"],
		plan_id=row["plan_id"],
		case_name=row["case_name"],
		description=row.get("description"),
		module=row.get("module"),
		function_point=row.get("function_point"),
		start_url=row["start_url"],
		steps=steps,
		global_variables=global_variables,
		variable_values=variable_values,
		status=row["status"],
		execution_order=row.get("execution_order"),
		created_at=row["created_at"],
		updated_at=row["updated_at"],
	)


class TestPlanService:
	"""Service for managing test plans, cases, and variable sets."""

	# ── Test Plan CRUD ──────────────────────────────────────────────────────

	async def create_plan(self, data: TestPlanCreate) -> TestPlanView:
		"""Create a new test plan."""
		plan_id = uuid7str()
		now = datetime.now().isoformat()
		self._log_create_plan(data.name)

		db = await get_db()
		try:
			await db.execute(
				"""INSERT INTO test_plans
				   (id, name, description, source_file_name, max_concurrency, status, created_at, updated_at)
				   VALUES (?, ?, ?, ?, ?, 'draft', ?, ?)""",
				(plan_id, data.name, data.description, data.source_file_name, data.max_concurrency, now, now),
			)
			await db.commit()
		finally:
			await db.close()

		plan = await self.get_plan(plan_id)
		assert plan is not None
		return plan

	async def get_plan(self, plan_id: str) -> TestPlanView | None:
		"""Get a test plan by ID."""
		db = await get_db()
		try:
			cursor = await db.execute("SELECT * FROM test_plans WHERE id = ?", (plan_id,))
			row = await cursor.fetchone()
			if row is None:
				return None
			d = _row_to_dict(row)
			return TestPlanView(**d)
		finally:
			await db.close()

	async def list_plans(self) -> list[TestPlanView]:
		"""List all test plans ordered by creation time descending."""
		db = await get_db()
		try:
			cursor = await db.execute(
				"SELECT tp.*, "
				"(SELECT COUNT(*) FROM test_cases tc WHERE tc.plan_id = tp.id) AS case_count "
				"FROM test_plans tp ORDER BY tp.created_at DESC"
			)
			rows = await cursor.fetchall()
			return [TestPlanView(**_row_to_dict(row)) for row in rows]
		finally:
			await db.close()

	async def update_plan(self, plan_id: str, data: TestPlanUpdate) -> TestPlanView:
		"""Update a test plan. Raises ValueError if not found."""
		existing = await self.get_plan(plan_id)
		if existing is None:
			raise ValueError(f"Test plan not found: {plan_id}")

		now = datetime.now().isoformat()
		updates = data.model_dump(exclude_none=True)
		if not updates:
			return existing

		# Validate against whitelist to prevent SQL injection
		invalid_keys = set(updates) - _PLAN_UPDATE_FIELDS
		if invalid_keys:
			raise ValueError(f"Invalid update fields: {invalid_keys}")

		set_clauses = ", ".join(f"{k} = ?" for k in updates)
		values = list(updates.values()) + [now, plan_id]

		db = await get_db()
		try:
			await db.execute(
				f"UPDATE test_plans SET {set_clauses}, updated_at = ? WHERE id = ?",
				values,
			)
			await db.commit()
		finally:
			await db.close()

		updated = await self.get_plan(plan_id)
		assert updated is not None
		return updated

	async def delete_plan(self, plan_id: str) -> bool:
		"""Delete a test plan and all its cases, runs, and results. Returns True if deleted."""
		db = await get_db()
		try:
			# Delete test_replays linked to results of this plan's cases
			# (must delete replays BEFORE results because result_id has no CASCADE)
			await db.execute(
				"DELETE FROM test_replays WHERE result_id IN "
				"(SELECT id FROM test_results WHERE case_id IN "
				"(SELECT id FROM test_cases WHERE plan_id = ?))",
				(plan_id,),
			)
			# Delete test_results whose case_id belongs to any case of this plan
			await db.execute(
				"DELETE FROM test_results WHERE case_id IN "
				"(SELECT id FROM test_cases WHERE plan_id = ?)",
				(plan_id,),
			)
			# Delete runs
			await db.execute("DELETE FROM test_runs WHERE plan_id = ?", (plan_id,))
			# Delete plan (cascades to test_cases and variable_sets)
			result = await db.execute("DELETE FROM test_plans WHERE id = ?", (plan_id,))
			await db.commit()
			deleted = result.rowcount > 0
			self._log_delete_plan(plan_id, deleted)
			return deleted
		finally:
			await db.close()

	async def confirm_plan(self, plan_id: str) -> TestPlanView:
		"""Confirm a plan (draft → confirmed). Raises ValueError if not in draft status."""
		existing = await self.get_plan(plan_id)
		if existing is None:
			raise ValueError(f"Test plan not found: {plan_id}")
		if existing.status != "draft":
			raise ValueError(f"Plan {plan_id} is not in draft status (current: {existing.status})")

		now = datetime.now().isoformat()
		db = await get_db()
		try:
			await db.execute(
				"UPDATE test_plans SET status = 'confirmed', updated_at = ? WHERE id = ?",
				(now, plan_id),
			)
			await db.commit()
		finally:
			await db.close()

		confirmed = await self.get_plan(plan_id)
		assert confirmed is not None
		return confirmed

	# ── Test Case CRUD ──────────────────────────────────────────────────────

	async def create_case(self, plan_id: str, data: TestCaseCreate) -> TestCaseView:
		"""Create a test case under a plan. Raises ValueError if plan not found."""
		plan = await self.get_plan(plan_id)
		if plan is None:
			raise ValueError(f"Test plan not found: {plan_id}")

		case_id = uuid7str()
		now = datetime.now().isoformat()
		steps_json = json.dumps([s.model_dump() for s in data.steps])
		global_vars_json = json.dumps(data.global_variables)
		variable_values_json = json.dumps(data.variable_values)

		db = await get_db()
		try:
			await db.execute(
				"""INSERT INTO test_cases
				   (id, plan_id, case_name, description, module, function_point,
				    start_url, steps_json, global_variables, variable_values_json,
				    status, execution_order, created_at, updated_at)
				   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
				(
					case_id, plan_id, data.case_name, data.description, data.module,
					data.function_point, data.start_url, steps_json, global_vars_json,
					variable_values_json, data.execution_order, now, now,
				),
			)
			await db.commit()
		finally:
			await db.close()

		case = await self.get_case(case_id)
		assert case is not None
		return case

	async def get_case(self, case_id: str) -> TestCaseView | None:
		"""Get a test case by ID."""
		db = await get_db()
		try:
			cursor = await db.execute("SELECT * FROM test_cases WHERE id = ?", (case_id,))
			row = await cursor.fetchone()
			if row is None:
				return None
			return _parse_case_row(_row_to_dict(row))
		finally:
			await db.close()

	async def list_cases(self, plan_id: str) -> list[TestCaseView]:
		"""List all test cases for a plan, ordered by execution_order then created_at."""
		db = await get_db()
		try:
			cursor = await db.execute(
				"SELECT * FROM test_cases WHERE plan_id = ? ORDER BY execution_order ASC, created_at ASC",
				(plan_id,),
			)
			rows = await cursor.fetchall()
			return [_parse_case_row(_row_to_dict(row)) for row in rows]
		finally:
			await db.close()

	async def update_case(self, case_id: str, data: TestCaseUpdate) -> TestCaseView:
		"""Update a test case. Raises ValueError if not found."""
		existing = await self.get_case(case_id)
		if existing is None:
			raise ValueError(f"Test case not found: {case_id}")

		now = datetime.now().isoformat()
		raw = data.model_dump(exclude_none=True)

		# Serialize complex fields
		if "steps" in raw:
			raw["steps_json"] = json.dumps([s.model_dump() for s in data.steps])
			del raw["steps"]
		if "global_variables" in raw:
			raw["global_variables"] = json.dumps(raw["global_variables"])
		if "variable_values" in raw:
			raw["variable_values_json"] = json.dumps(raw["variable_values"])
			del raw["variable_values"]

		if not raw:
			return existing

		# Validate against whitelist to prevent SQL injection
		invalid_keys = set(raw) - _CASE_UPDATE_FIELDS
		if invalid_keys:
			raise ValueError(f"Invalid update fields: {invalid_keys}")

		set_clauses = ", ".join(f"{k} = ?" for k in raw)
		values = list(raw.values()) + [now, case_id]

		db = await get_db()
		try:
			await db.execute(
				f"UPDATE test_cases SET {set_clauses}, updated_at = ? WHERE id = ?",
				values,
			)
			await db.commit()
		finally:
			await db.close()

		updated = await self.get_case(case_id)
		assert updated is not None
		return updated

	async def delete_case(self, case_id: str) -> bool:
		"""Delete a test case and its variable sets. Returns True if deleted."""
		db = await get_db()
		try:
			result = await db.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
			await db.commit()
			return result.rowcount > 0
		finally:
			await db.close()

	# ── Variable Sets ───────────────────────────────────────────────────────

	async def create_variable_sets(
		self, case_id: str, variable_sets: list[dict[str, str]]
	) -> list[VariableSetView]:
		"""Create variable sets for a case. Raises ValueError if case not found.
		Filters out variable sets where all values are empty strings."""
		case = await self.get_case(case_id)
		if case is None:
			raise ValueError(f"Test case not found: {case_id}")

		now = datetime.now().isoformat()
		created: list[VariableSetView] = []

		filtered_sets = [
			vs for vs in variable_sets
			if any(v.strip() for v in vs.values())
		]

		db = await get_db()
		try:
			for idx, variables in enumerate(filtered_sets):
				vs_id = uuid7str()
				variables_json = json.dumps(variables)
				await db.execute(
					"""INSERT INTO test_case_variable_sets
					   (id, case_id, set_index, variables_json, status, created_at)
					   VALUES (?, ?, ?, ?, 'pending', ?)""",
					(vs_id, case_id, idx, variables_json, now),
				)
				created.append(
					VariableSetView(
						id=vs_id,
						case_id=case_id,
						set_index=idx,
						variables=variables,
						status="pending",
						created_at=now,
					)
				)
			await db.commit()
		finally:
			await db.close()

		return created

	async def get_variable_sets(self, case_id: str) -> list[VariableSetView]:
		"""Get all variable sets for a case, ordered by set_index."""
		db = await get_db()
		try:
			cursor = await db.execute(
				"SELECT * FROM test_case_variable_sets WHERE case_id = ? ORDER BY set_index ASC",
				(case_id,),
			)
			rows = await cursor.fetchall()
			result = []
			for row in rows:
				d = _row_to_dict(row)
				result.append(
					VariableSetView(
						id=d["id"],
						case_id=d["case_id"],
						set_index=d["set_index"],
						variables=json.loads(d["variables_json"]),
						status=d["status"],
						created_at=d["created_at"],
					)
				)
			return result
		finally:
			await db.close()

	async def delete_variable_set(self, variable_set_id: str) -> bool:
		"""Delete a single variable set by ID. Returns True if deleted."""
		db = await get_db()
		try:
			result = await db.execute(
				"DELETE FROM test_case_variable_sets WHERE id = ?",
				(variable_set_id,),
			)
			await db.commit()
			return result.rowcount > 0
		finally:
			await db.close()

	# ── Bulk Import ─────────────────────────────────────────────────────────

	async def import_parsed_plan(
		self,
		parsed: TestPlanParsedSchema,
		name: str,
		source_file_name: str | None = None,
		max_concurrency: int = 3,
	) -> TestPlanDetailView:
		"""
		Import a fully parsed plan (from LLM) into the database atomically.

		All inserts (plan + cases + variable sets) run in a single connection
		and transaction — partial failure rolls back everything.
		"""
		self._log_import_plan(name, len(parsed.test_cases))

		plan_id = uuid7str()
		now = datetime.now().isoformat()

		db = await get_db()
		try:
			await db.execute("BEGIN")
			# Insert plan
			await db.execute(
				"""INSERT INTO test_plans
				   (id, name, description, source_file_name, max_concurrency, status, created_at, updated_at)
				   VALUES (?, ?, ?, ?, ?, 'draft', ?, ?)""",
				(plan_id, name, None, source_file_name, max_concurrency, now, now),
			)

			cases: list[TestCaseView] = []
			for order, parsed_case in enumerate(parsed.test_cases):
				case_id = uuid7str()
				steps_json = json.dumps([s.model_dump() for s in parsed_case.steps])
				global_vars_json = json.dumps(parsed_case.global_variables)
				await db.execute(
					"""INSERT INTO test_cases
					   (id, plan_id, case_name, description, module, function_point,
					    start_url, steps_json, global_variables, variable_values_json,
					    status, execution_order, created_at, updated_at)
					   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', 'pending', ?, ?, ?)""",
					(
						case_id, plan_id, parsed_case.case_name, parsed_case.description,
						parsed_case.module, parsed_case.function_point, parsed_case.start_url,
						steps_json, global_vars_json, order, now, now,
					),
				)

				# Insert variable sets
				for idx, variables in enumerate(parsed_case.variable_sets or []):
					vs_id = uuid7str()
					await db.execute(
						"""INSERT INTO test_case_variable_sets
						   (id, case_id, set_index, variables_json, status, created_at)
						   VALUES (?, ?, ?, ?, 'pending', ?)""",
						(vs_id, case_id, idx, json.dumps(variables), now),
					)

				cases.append(TestCaseView(
					id=case_id,
					plan_id=plan_id,
					case_name=parsed_case.case_name,
					description=parsed_case.description,
					module=parsed_case.module,
					function_point=parsed_case.function_point,
					start_url=parsed_case.start_url,
					steps=parsed_case.steps,
					global_variables=parsed_case.global_variables,
					variable_values={},
					status="pending",
					execution_order=order,
					created_at=now,
					updated_at=now,
				))

			await db.commit()
		except Exception:
			await db.execute("ROLLBACK")
			raise
		finally:
			await db.close()

		return TestPlanDetailView(
			id=plan_id,
			name=name,
			description=None,
			source_file_name=source_file_name,
			max_concurrency=max_concurrency,
			status="draft",
			created_at=now,
			updated_at=now,
			cases=cases,
		)

	async def get_plan_detail(self, plan_id: str) -> TestPlanDetailView | None:
		"""Get a plan with all its cases."""
		plan = await self.get_plan(plan_id)
		if plan is None:
			return None
		cases = await self.list_cases(plan_id)
		return TestPlanDetailView(
			id=plan.id,
			name=plan.name,
			description=plan.description,
			source_file_name=plan.source_file_name,
			max_concurrency=plan.max_concurrency,
			status=plan.status,
			created_at=plan.created_at,
			updated_at=plan.updated_at,
			cases=cases,
		)

	# ── Logging helpers ─────────────────────────────────────────────────────

	def _log_create_plan(self, name: str) -> None:
		logger.info(f"Creating test plan: {name}")

	def _log_delete_plan(self, plan_id: str, deleted: bool) -> None:
		if deleted:
			logger.info(f"Deleted test plan: {plan_id}")
		else:
			logger.warning(f"Test plan not found for deletion: {plan_id}")

	def _log_import_plan(self, name: str, case_count: int) -> None:
		logger.info(f"Importing parsed plan '{name}' with {case_count} cases")


# Global singleton instance
test_plan_service = TestPlanService()
