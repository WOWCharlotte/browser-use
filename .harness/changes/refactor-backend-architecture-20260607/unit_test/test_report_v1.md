# Unit Test Report v1

## Tests Added
- `tests/test_persistence.py`
  - Canonical schema file initialization and dynamic database path behavior.
- `tests/test_execution_service.py`
  - `TestPromptBuilder` variable substitution and completion criteria.
  - `ExecutionRuntimeState` runtime tracking behavior.
- `tests/test_agui.py`
  - Extracted AG-UI event mapper, input parser, and HITL coordinator behavior.
- `tests/test_app_factory.py`
  - `create_app()` route registration and global `app` compatibility.

## Passing Verification
- `uv run pytest tests/test_persistence.py tests/test_test_plan_service.py -v`
  - Result: 60 passed.
- `uv run pytest tests/test_execution_service.py -v`
  - Result: 17 passed.
- `uv run pytest tests/test_agui.py -v`
  - Result: 39 passed.
- `uv run pytest tests/test_app_factory.py tests/test_persistence.py tests/test_test_plan_service.py tests/test_execution_service.py tests/test_agui.py -v`
  - Result: 118 passed.

## Full Suite
- `uv run pytest tests -v`
  - Result: 162 passed, 6 failed before `/api/chat` compatibility.
- After adding `/api/chat`, `uv run pytest tests/test_integration.py -v`
  - Result: 9 passed, 2 failed.
  - Remaining failures are test harness/version issues described in `ci_result_v1.md`.
