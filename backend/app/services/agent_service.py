import asyncio
import uuid
from typing import Any, Awaitable, Callable

from app.config import Config
from app.services.browser_service import browser_service
from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI

# ============================================================================
# AG-UI 事件类型常量
# ============================================================================

# 生命周期事件
EVENT_RUN_STARTED = "RUN_STARTED"
EVENT_RUN_FINISHED = "RUN_FINISHED"
EVENT_RUN_ERROR = "RUN_ERROR"

# 消息事件
EVENT_TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
EVENT_TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
EVENT_TEXT_MESSAGE_END = "TEXT_MESSAGE_END"

# 工具调用事件
EVENT_TOOL_CALL_START = "TOOL_CALL_START"
EVENT_TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
EVENT_TOOL_CALL_RESULT = "TOOL_CALL_RESULT"
EVENT_TOOL_CALL_END = "TOOL_CALL_END"

# 步骤事件
EVENT_STEP_STARTED = "STEP_STARTED"
EVENT_STEP_FINISHED = "STEP_FINISHED"

# 状态事件
EVENT_STATE_SNAPSHOT = "STATE_SNAPSHOT"
EVENT_STATE_DELTA = "STATE_DELTA"

# HITL 中断事件
EVENT_INTERRUPT = "INTERRUPT"
EVENT_RESUME = "RESUME"


class AgentService:
	def __init__(self) -> None:
		self._agents: dict[str, Agent] = {}
		self._paused: dict[str, bool] = {}
		self._resume_events: dict[str, asyncio.Event] = {}
		self._run_tasks: dict[str, asyncio.Task] = {}
		self._history: dict[str, list[dict[str, Any]]] = {}

	def _create_llm(self) -> ChatOpenAI:
		return ChatOpenAI(
			model=Config.LLM_MODEL,
			api_key=Config.LLM_API_KEY,
			base_url=Config.LLM_BASE_URL,
		)

	async def create_agent(self, session_id: str, task: str) -> Agent:
		llm = self._create_llm()
		agent = Agent(
			task=task,
			llm=llm,
			use_vision=True,
			max_actions_per_step=1,
		)
		self._agents[session_id] = agent
		self._paused[session_id] = False
		self._resume_events[session_id] = asyncio.Event()
		self._history[session_id] = []
		return agent

	def _build_step_content(self, last_item: Any) -> list[str]:
		"""Extract step content from agent history item."""
		parts = []
		if last_item.model_output:
			output = last_item.model_output
			if output.thinking:
				parts.append(f"思考: {output.thinking}")
			if output.memory:
				parts.append(f"记忆: {output.memory}")
			if output.evaluation_previous_goal:
				parts.append(f"上一步评估: {output.evaluation_previous_goal}")
			if output.next_goal:
				parts.append(f"下一步目标: {output.next_goal}")
			if output.plan_update:
				parts.append(f"计划更新: {' -> '.join(output.plan_update)}")
		if last_item.result:
			for result in last_item.result:
				if result.error:
					parts.append(f"Error: {result.error}")
				elif result.long_term_memory:
					parts.append(f"长期记忆: {result.long_term_memory}")
				elif result.extracted_content:
					parts.append(result.extracted_content)
		return parts

	def _build_snapshot_state(self, state: Any, history: list[dict[str, Any]]) -> dict[str, Any]:
		"""Build snapshot state from browser state."""
		tabs_data = [tab.model_dump() for tab in state.tabs] if state.tabs else []
		interacted_data = []
		if state.interacted_element:
			for el in state.interacted_element:
				if el:
					try:
						interacted_data.append(el.to_dict())
					except Exception:
						interacted_data.append(None)
				else:
					interacted_data.append(None)
		return {
			"url": state.url,
			"title": state.title,
			"tabs": tabs_data,
			"interacted_element": interacted_data,
			"screenshot": state.get_screenshot(),
			"history": list(history),
		}

	async def _persist_step(self, session_id: str, state: Any, content_parts: list[str]) -> None:
		"""Persist step data to DB."""
		try:
			from app.services.session_service import session_service
			if content_parts:
				await session_service.add_message(session_id, "assistant", "<br>".join(content_parts))
			await session_service.add_browser_state(
				session_id=session_id,
				url=state.url,
				title=state.title,
				screenshot=state.get_screenshot(),
			)
		except Exception as e:
			print(f"Error persisting step data: {e}")

	async def run_agent(
		self,
		session_id: str,
		message: str,
		on_event: Callable[[dict[str, Any]], Awaitable[None]],
		max_steps: int = 100,
	) -> None:
		"""Run agent with AG-UI compatible event callbacks.

		Runs the agent to completion (or until stopped/paused) and reports
		events via the on_event callback using AG-UI event format.
		"""
		if session_id not in browser_service._sessions:
			await browser_service.create_session(session_id)

		agent = await self.create_agent(session_id, message)
		step_count = 0
		message_id = str(uuid.uuid4())

		async def on_step_start(agent_instance: Agent) -> None:
			"""Callback called before each step - emit STEP_STARTED."""
			nonlocal step_count, message_id
			step_count = agent_instance.state.n_steps
			message_id = str(uuid.uuid4())
			await on_event({
				"type": EVENT_TEXT_MESSAGE_START,
				"message_id": message_id,
				"role": "assistant",
			})

			if self._paused.get(session_id, False):
				self._resume_events[session_id].clear()
				await on_event({
					"type": EVENT_INTERRUPT,
					"interrupt_id": str(uuid.uuid4()),
					"reason": "awaiting_user",
					"step": step_count,
				})
				await self._resume_events[session_id].wait()
				await on_event({"type": EVENT_RESUME, "step": step_count})

			await on_event({"type": EVENT_STEP_STARTED, "step_name": f"Step {step_count}"})

		async def on_step_end(agent_instance: Agent) -> None:
			"""Callback called after each step - emit STEP_FINISHED and content events."""
			nonlocal step_count, message_id
			step_count = agent_instance.state.n_steps

			if not agent_instance.history or not agent_instance.history.history:
				return

			last_item = agent_instance.history.history[-1]
			content_parts = self._build_step_content(last_item)

			if content_parts:
				await on_event({
					"type": EVENT_TEXT_MESSAGE_CONTENT,
					"message_id": message_id,
					"content": "<br>".join(content_parts),
				})

			await on_event({"type": EVENT_TEXT_MESSAGE_END, "message_id": message_id})
			await on_event({"type": EVENT_STEP_FINISHED, "step_name": f"Step {step_count}"})

			state = last_item.state
			snapshot_state = self._build_snapshot_state(state, self._history[session_id])
			self._history[session_id].append(snapshot_state)
			await on_event({"type": EVENT_STATE_SNAPSHOT, "state": snapshot_state})

			await self._persist_step(session_id, state, content_parts)

		try:
			history = await agent.run(
				max_steps=max_steps,
				on_step_start=on_step_start,
				on_step_end=on_step_end,
			)

			if history:
				final_result = history.final_result()
				if final_result:
					final_message_id = str(uuid.uuid4())
					await on_event({
						"type": EVENT_TEXT_MESSAGE_START,
						"message_id": final_message_id,
						"role": "assistant",
					})
					await on_event({
						"type": EVENT_TEXT_MESSAGE_CONTENT,
						"message_id": final_message_id,
						"content": str(final_result),
					})
					await on_event({"type": EVENT_TEXT_MESSAGE_END, "message_id": final_message_id})
					try:
						from app.services.session_service import session_service
						await session_service.add_message(session_id, "assistant", str(final_result))
					except Exception as e:
						print(f"Error persisting final result: {e}")

		except Exception as e:
			await on_event({
				"type": EVENT_RUN_ERROR,
				"error": str(e),
				"code": "500",
			})
		finally:
			await on_event({"type": "DONE", "step": step_count})

	def pause_agent(self, session_id: str) -> None:
		"""Pause agent at next step boundary."""
		if session_id in self._agents:
			self._paused[session_id] = True
			self._agents[session_id].pause()

	def resume_agent(self, session_id: str) -> None:
		"""Resume a paused agent."""
		if session_id in self._agents and self._paused.get(session_id, False):
			self._paused[session_id] = False
			self._resume_events[session_id].set()
			self._agents[session_id].resume()

	def stop_agent(self, session_id: str) -> None:
		"""Stop agent execution."""
		if session_id in self._agents:
			self._paused[session_id] = False
			self._resume_events[session_id].set()
			self._agents[session_id].stop()

	def get_status(self, session_id: str) -> str:
		"""Get agent status: stopped, running, or paused."""
		if session_id not in self._agents:
			return "stopped"
		agent = self._agents[session_id]
		if self._paused.get(session_id, False):
			return "paused"
		if agent.state.paused:
			return "paused"
		if agent.state.stopped:
			return "stopped"
		return "running"

	def get_agent(self, session_id: str) -> Agent | None:
		"""Get agent instance for a session."""
		return self._agents.get(session_id)


agent_service = AgentService()