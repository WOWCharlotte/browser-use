import asyncio
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator

router = APIRouter()


class ChatRequest(BaseModel):
	session_id: str
	message: str
	attachments: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
	from app.services.agent_service import agent_service
	from app.services.session_service import session_service

	# Save user message
	try:
		await session_service.add_message(req.session_id, "user", req.message)
	except Exception as e:
		pass  # Log error in production

	async def event_generator() -> AsyncGenerator[str, None]:
		async def on_event(event: dict) -> None:
			data = json.dumps(event)
			yield f"data: {data}\n\n"

		try:
			async for _ in agent_service.run_agent(req.session_id, req.message, on_event):
				# The async generator yields None but we handle events via callback
				pass
		except Exception as e:
			yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

	return StreamingResponse(event_generator(), media_type="text/event-stream")