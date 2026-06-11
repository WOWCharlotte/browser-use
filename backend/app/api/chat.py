import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from app.services.session_service import session_service

router = APIRouter()


class ChatRequest(BaseModel):
	"""Compatibility request body for the legacy chat endpoint."""

	model_config = ConfigDict(extra="forbid")

	session_id: str
	message: str
	attachments: list[dict[str, Any]] = []


@router.post("/chat")
async def chat_endpoint(req: ChatRequest) -> StreamingResponse:
	"""Legacy SSE chat endpoint kept for integration compatibility."""
	await session_service.add_message(req.session_id, "user", req.message)

	async def event_generator():
		payload = {"type": "message", "content": "Chat endpoint is available."}
		yield f"data: {json.dumps(payload)}\n\n"

	return StreamingResponse(event_generator(), media_type="text/event-stream")
