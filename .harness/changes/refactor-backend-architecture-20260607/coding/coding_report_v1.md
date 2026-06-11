# Coding Report v1

## Implemented
- Added canonical DB schema at `backend/app/db/schema.sql`.
- Refactored `backend/app/db/database.py` to load schema SQL and preserve legacy `DB_PATH` patch compatibility.
- Added execution components:
  - `app/services/execution/prompt_builder.py`
  - `app/services/execution/runtime_state.py`
- Added AG-UI components:
  - `app/services/agui/input_parser.py`
  - `app/services/agui/event_mapper.py`
  - `app/services/agui/hitl.py`
- Added `create_app(settings=None)` and FastAPI lifespan startup while preserving global `app`.
- Added `BackendSettings` for app construction state.
- Added legacy `/api/chat` SSE compatibility route used by integration tests.

## Compatibility
- Existing `/api/*` routes remain registered.
- Existing `from app import app` import still works.
- Existing `app.db.database.DB_PATH` test patching remains supported.
- Existing AG-UI helper imports from `app.api.agui` remain supported.

## Known Limitations
- `TestExecutionService._build_task_prompt()` delegates to the new builder, but the old body remains after the return because the file contains encoded text that resisted safe contextual deletion.
