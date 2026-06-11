# CI Result v1

## Commands
- `uv run pytest tests/test_persistence.py tests/test_test_plan_service.py -v`
  - Passed: 60.
- `uv run pytest tests/test_execution_service.py -v`
  - Passed: 17.
- `uv run pytest tests/test_agui.py -v`
  - Passed: 39.
- `uv run pytest tests/test_app_factory.py tests/test_persistence.py tests/test_test_plan_service.py tests/test_execution_service.py tests/test_agui.py -v`
  - Passed: 118.
- `uv run pytest tests -v`
  - Result after refactor: 162 passed, 6 failed.
- `uv run pytest tests/test_integration.py -v` after `/api/chat` compatibility route
  - Result: 9 passed, 2 failed.
- Final focused verification after all edits:
  - `uv run pytest tests/test_app_factory.py tests/test_persistence.py tests/test_test_plan_service.py tests/test_execution_service.py tests/test_agui.py -v`
  - Result: 118 passed, 13 warnings.

## Remaining Failures
- `tests/test_integration.py::test_chat_endpoint_basic`
  - Uses `httpx.AsyncClient(base_url="http://test")` without ASGI transport; request goes over network and returns `502`.
- `tests/test_integration.py::test_chat_endpoint_content_type`
  - Calls `TestClient.post(..., stream=True)`; installed TestClient does not accept `stream`.

## Pre-Commit
- `uv run pre-commit run --all-files`
  - Failed before hooks ran because pre-commit could not create a Python 3.11 hook environment: `failed to find interpreter for python_spec='python3.11'`.
