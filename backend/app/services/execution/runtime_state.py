import asyncio
from typing import Any


class ExecutionRuntimeState:
	"""In-memory runtime state for active test executions."""

	def __init__(self) -> None:
		self.active_tasks: dict[str, set[asyncio.Task[Any]]] = {}
		self.active_sessions: dict[str, list[Any]] = {}
		self.active_loggers: dict[str, Any] = {}
		self.active_agents: dict[str, Any] = {}
		self.result_sessions: dict[str, Any] = {}
		self.pause_events: dict[str, asyncio.Event] = {}
		self.paused: dict[str, bool] = {}

	def add_run_task(self, run_id: str, task: asyncio.Task[Any]) -> None:
		self.active_tasks.setdefault(run_id, set()).add(task)

	def get_run_tasks(self, run_id: str) -> set[asyncio.Task[Any]]:
		return self.active_tasks.get(run_id, set())

	def clear_run(self, run_id: str) -> None:
		self.active_tasks.pop(run_id, None)
		self.active_sessions.pop(run_id, None)

	def add_run_session(self, run_id: str, session: Any) -> None:
		self.active_sessions.setdefault(run_id, []).append(session)

	def remove_run_session(self, run_id: str, session: Any) -> None:
		if run_id not in self.active_sessions:
			return
		try:
			self.active_sessions[run_id].remove(session)
		except ValueError:
			pass

	def get_run_sessions(self, run_id: str) -> list[Any]:
		return self.active_sessions.get(run_id, [])

	def set_result_logger(self, result_id: str, logger: Any) -> None:
		self.active_loggers[result_id] = logger

	def get_result_logger(self, result_id: str) -> Any | None:
		return self.active_loggers.get(result_id)

	def clear_result_logger(self, result_id: str) -> None:
		self.active_loggers.pop(result_id, None)

	def set_result_agent(self, result_id: str, agent: Any) -> None:
		self.active_agents[result_id] = agent

	def get_result_agent(self, result_id: str) -> Any | None:
		return self.active_agents.get(result_id)

	def set_result_session(self, result_id: str, session: Any) -> None:
		self.result_sessions[result_id] = session

	def get_result_session(self, result_id: str) -> Any | None:
		return self.result_sessions.get(result_id)

	def create_pause_event(self, result_id: str) -> asyncio.Event:
		event = asyncio.Event()
		event.set()
		self.pause_events[result_id] = event
		self.paused[result_id] = False
		return event

	def get_pause_event(self, result_id: str) -> asyncio.Event | None:
		return self.pause_events.get(result_id)

	def set_paused(self, result_id: str, paused: bool) -> None:
		self.paused[result_id] = paused

	def is_paused(self, result_id: str) -> bool:
		return self.paused.get(result_id, False)

	def clear_result(self, result_id: str) -> None:
		self.active_agents.pop(result_id, None)
		self.result_sessions.pop(result_id, None)
		self.pause_events.pop(result_id, None)
		self.paused.pop(result_id, None)
		self.active_loggers.pop(result_id, None)
