# Backend Architecture Refactor Tasks

## P0 Database Schema
- Add `backend/app/db/schema.sql` as the single schema source.
- Add tests proving `init_db()` creates required tables from the canonical SQL.
- Replace duplicated test schema setup with shared initialization where practical.

## P1 Execution Engine
- Extract runtime state tracking from `TestExecutionService`.
- Extract artifact persistence and screenshot retrieval helpers.
- Extract prompt building into a focused component.
- Preserve `TestExecutionService` public API.

## P1 AG-UI Orchestration
- Extract input parsing and event mapping from `api/agui.py`.
- Add an injectable in-memory HITL coordinator.
- Preserve `/api/agui` and `/api/agui/resume/{session_id}` behavior.

## P2 App Factory and Settings
- Add `create_app(settings=None)` and preserve global `app`.
- Move startup work to lifespan helpers.
- Add settings model while preserving existing config access.

## Acceptance Criteria
- Focused tests pass after each priority batch.
- Full backend test suite passes.
- Harness reports are updated with implementation and verification evidence.
