.PHONY: browser-server install

browser-server:
	@echo "Starting backend (FastAPI on port 8888)..."
	@cd backend && uv run python -m app.main &
	@echo "Starting frontend (Next.js on port 3000)..."
	@cd frontend && npm run dev