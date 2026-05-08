from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AgentControlRequest(BaseModel):
	session_id: str


@router.post("/agent/pause")
async def pause_agent(req: AgentControlRequest):
	from app.services.agent_service import agent_service
	try:
		agent_service.pause_agent(req.session_id)
		return {"status": "paused"}
	except Exception as e:
		return {"status": "error", "message": str(e)}


@router.post("/agent/resume")
async def resume_agent(req: AgentControlRequest):
	from app.services.agent_service import agent_service
	try:
		agent_service.resume_agent(req.session_id)
		return {"status": "running"}
	except Exception as e:
		return {"status": "error", "message": str(e)}


@router.post("/agent/stop")
async def stop_agent(req: AgentControlRequest):
	from app.services.agent_service import agent_service
	try:
		agent_service.stop_agent(req.session_id)
		return {"status": "stopped"}
	except Exception as e:
		return {"status": "error", "message": str(e)}


@router.get("/agent/status/{session_id}")
async def get_status(session_id: str):
	from app.services.agent_service import agent_service
	return {"status": agent_service.get_status(session_id)}