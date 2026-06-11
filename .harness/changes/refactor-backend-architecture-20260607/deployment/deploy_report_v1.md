# Deployment Verification v1

## Command
- `uv run python -c "from app import app, create_app; created = create_app(); print(app.title); print(created.title); print(any(route.path == '/api/chat' for route in created.routes))"`

## Result
- Passed.
- Output:
  - `AI Workspace Backend`
  - `AI Workspace Backend`
  - `True`

## Notes
- This verifies importability, app factory construction, global app compatibility, and `/api/chat` route registration.
