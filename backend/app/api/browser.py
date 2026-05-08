from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

router = APIRouter()

VALID_ACTIONS: set[str] = {"create", "close", "navigate", "click", "type", "scroll", "screenshot"}


class BrowserControlRequest(BaseModel):
	session_id: str
	action: str
	args: dict[str, Any] = {}


class BrowserControlResponse(BaseModel):
	success: bool
	state: dict


@router.post("/browser/control")
async def control_browser(req: BrowserControlRequest):
	from app.services.browser_service import browser_service
	if req.action not in VALID_ACTIONS:
		return BrowserControlResponse(success=False, state={"error": f"Unknown action: {req.action}"})
	if req.action == "create":
		state = await browser_service.create_session(req.session_id)
		return BrowserControlResponse(success=True, state=state)
	elif req.action == "close":
		await browser_service.close_session(req.session_id)
		return BrowserControlResponse(success=True, state={})
	else:
		state = await browser_service.execute_action(req.session_id, req.action, req.args)
		success = state.get("success", True) and "error" not in state
		return BrowserControlResponse(success=success, state=state)


@router.get("/browser/state/{session_id}")
async def get_browser_state(session_id: str):
	from app.services.browser_service import browser_service
	state = await browser_service.get_state(session_id)
	return state