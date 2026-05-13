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
		event_queue: asyncio.Queue[dict] = asyncio.Queue()

		async def on_event(event: dict) -> None:
			await event_queue.put(event)

		try:
			# Start the agent task
			agent_task = asyncio.create_task(
				agent_service.run_agent(req.session_id, req.message, on_event)
			)

			# Yield events as they come in
			while True:
				try:
					event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
					yield f"data: {json.dumps(event)}\n\n"
					if event.get("type") in ("done", "error"):
						break
				except asyncio.TimeoutError:
					# Send heartbeat to keep connection alive
					yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
		except Exception as e:
			yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
		finally:
			# Cancel agent task if still running
			if not agent_task.done():
				agent_task.cancel()

	return StreamingResponse(event_generator(), media_type="text/event-stream")