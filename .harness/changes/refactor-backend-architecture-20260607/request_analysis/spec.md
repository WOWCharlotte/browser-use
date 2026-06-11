# Backend Architecture Refactor Spec

## Goal
Refactor the backend architecture without changing public API behavior, database table names, environment variable names, or Browser Use model behavior.

## Scope
- Add a canonical SQL schema file and make database initialization read from it.
- Split the large test execution service into focused components while preserving its public methods.
- Split AG-UI route internals into input parsing, event mapping, HITL coordination, and orchestration helpers while preserving route contracts.
- Add an application factory and lifespan startup path while keeping `from app import app` compatibility.
- Introduce settings support without replacing existing environment variables or model names.

## Non-Goals
- No frontend changes.
- No migration to Postgres or Alembic.
- No route shape, response shape, or table name changes.
- No model name replacement.

## Compatibility Guarantees
- Existing tests should continue to pass.
- Existing imports of global service singletons remain supported.
- Existing `.env` keys keep the same names and defaults.
- Existing `/api/*` endpoints remain unchanged.
