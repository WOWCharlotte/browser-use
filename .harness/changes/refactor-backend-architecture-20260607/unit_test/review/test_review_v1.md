# Test Review v1

## Decision
APPROVED WITH RESIDUAL RISK

## Review
- New architecture seams are covered by focused tests.
- Existing DB, test plan, execution, AG-UI, and app factory suites pass together.
- The remaining red integration checks do not exercise application code successfully because they fail before or outside ASGI routing.

## Required Follow-Up
- Update integration tests to use `ASGITransport` for async requests.
- Replace `TestClient.post(..., stream=True)` with the supported streaming API for the installed FastAPI/Starlette version.
