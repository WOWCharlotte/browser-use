from typing import Any

from ag_ui.core import (
	BaseEvent,
	CustomEvent,
	RunErrorEvent,
	RunFinishedEvent,
	RunStartedEvent,
	StateDeltaEvent,
	StateSnapshotEvent,
	StepFinishedEvent,
	StepStartedEvent,
	TextMessageContentEvent,
	TextMessageEndEvent,
	TextMessageStartEvent,
	ToolCallArgsEvent,
	ToolCallEndEvent,
	ToolCallResultEvent,
	ToolCallStartEvent,
)

from app.utils import uuid7str


def map_agent_event_to_agui(event: dict[str, Any]) -> BaseEvent | None:
	"""Map internal execution events to AG-UI protocol events."""
	event_type = event.get("type")
	run_id = event.get("run_id")
	thread_id = event.get("thread_id")

	if event_type == "STEP_STARTED":
		return StepStartedEvent(step_name=event.get("step_name", "Step"))
	if event_type == "STEP_FINISHED":
		return StepFinishedEvent(step_name=event.get("step_name", "Step"))
	if event_type == "TEXT_MESSAGE_START":
		return TextMessageStartEvent(
			message_id=event.get("message_id", uuid7str()),
			role=event.get("role", "assistant"),
		)
	if event_type == "TEXT_MESSAGE_CONTENT":
		return TextMessageContentEvent(
			message_id=event.get("message_id", ""),
			delta=event.get("content", ""),
		)
	if event_type == "TEXT_MESSAGE_END":
		return TextMessageEndEvent(message_id=event.get("message_id", ""))
	if event_type == "RUN_STARTED":
		return RunStartedEvent(
			thread_id=thread_id or uuid7str(),
			run_id=run_id or uuid7str(),
		)
	if event_type == "RUN_FINISHED":
		return RunFinishedEvent(
			thread_id=thread_id or uuid7str(),
			run_id=run_id or uuid7str(),
			result=event.get("result"),
		)
	if event_type == "RUN_ERROR":
		return RunErrorEvent(
			message=event.get("error", "Unknown error"),
			code=event.get("code"),
		)
	if event_type == "STATE_SNAPSHOT":
		return StateSnapshotEvent(snapshot=event.get("state", {}))
	if event_type == "STATE_DELTA":
		return StateDeltaEvent(delta=event.get("delta", []))
	if event_type == "TOOL_CALL_START":
		return ToolCallStartEvent(
			tool_call_id=event.get("tool_call_id", uuid7str()),
			tool_call_name=event.get("tool_call_name", "unknown"),
		)
	if event_type == "TOOL_CALL_ARGS":
		return ToolCallArgsEvent(
			tool_call_id=event.get("tool_call_id", ""),
			delta=event.get("delta", ""),
		)
	if event_type == "TOOL_CALL_END":
		return ToolCallEndEvent(tool_call_id=event.get("tool_call_id", ""))
	if event_type == "TOOL_CALL_RESULT":
		return ToolCallResultEvent(
			tool_call_id=event.get("tool_call_id", ""),
			message_id=event.get("message_id", uuid7str()),
			content=event.get("content", ""),
		)
	if event_type in ("INTERRUPT", "RESUME", "done", "heartbeat"):
		return None
	if event_type in ("PAUSE", "STOP"):
		return CustomEvent(name=event_type.lower(), value=event.get("value", {}))
	if event_type in ("DONE", "HEARTBEAT"):
		return CustomEvent(name=event_type.lower(), value=event.get("value", {}))
	return None
