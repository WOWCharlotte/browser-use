import asyncio


class InMemoryHitlCoordinator:
	"""Coordinate in-memory human-in-the-loop resume state."""

	def __init__(self) -> None:
		self._resume_events: dict[str, asyncio.Event] = {}
		self._resume_actions: dict[str, str] = {}

	def create_waiter(self, session_id: str) -> asyncio.Event:
		"""Create and register a waiter for a session."""
		event = asyncio.Event()
		self._resume_events[session_id] = event
		return event

	def clear_waiter(self, session_id: str) -> None:
		"""Clear a pending waiter for a session."""
		self._resume_events.pop(session_id, None)

	def resume(self, session_id: str, action: str = "confirm") -> bool:
		"""Resume a waiting session with an action."""
		event = self._resume_events.get(session_id)
		if event is None:
			return False
		self._resume_actions[session_id] = action
		event.set()
		return True

	def get_action(self, session_id: str, default: str = "confirm") -> str:
		"""Get and remove the stored resume action for a session."""
		return self._resume_actions.pop(session_id, default)
