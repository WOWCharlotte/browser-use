from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.session_service import session_service

router = APIRouter()


class CreateSessionRequest(BaseModel):
	title: Optional[str] = "New conversation"


class UpdateSessionRequest(BaseModel):
	title: str


@router.get("/sessions")
async def list_sessions():
	return await session_service.list_sessions()


@router.post("/sessions")
async def create_session(req: CreateSessionRequest):
	return await session_service.create_session(req.title or "New conversation")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
	session = await session_service.get_session(session_id)
	if not session:
		raise HTTPException(status_code=404, detail="Session not found")
	return session


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, req: UpdateSessionRequest):
	session = await session_service.update_session(session_id, req.title)
	if not session:
		raise HTTPException(status_code=404, detail="Session not found")
	return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
	success = await session_service.delete_session(session_id)
	if not success:
		raise HTTPException(status_code=404, detail="Session not found")
	return {"status": "ok"}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
	return await session_service.get_messages(session_id)


@router.get("/sessions/{session_id}/browser_states")
async def get_browser_states(session_id: str):
	return await session_service.get_browser_states(session_id)