import asyncio
from typing import Callable, Any

from browser_use import Agent
from browser_use.agent.service import AgentHookFunc
from browser_use.llm.openai.chat import ChatOpenAI

from app.config import Config
from app.services.browser_service import browser_service


class AgentService:
	def __init__(self) -> None:
		self._agents: dict[str, Agent] = {}
		self._paused: dict[str, bool] = {}
		self._resume_events: dict[str, asyncio.Event] = {}
		self._run_tasks: dict[str, asyncio.Task] = {}

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
		return agent

	async def run_agent(
		self,
		session_id: str,
		message: str,
		on_event: Callable[[dict[str, Any]], None],
		max_steps: int = 100,
	) -> None:
		"""Run agent with event callbacks.

		Runs the agent to completion (or until stopped/paused) and reports
		events via the on_event callback.
		"""
		agent = self._agents.get(session_id)
		if not agent:
			agent = await self.create_agent(session_id, message)
		else:
			agent.task = message

		step_count = 0

		async def on_step_start(agent_instance: Agent) -> None:
			"""Callback called before each step."""
			nonlocal step_count
			step_count = agent_instance.state.n_steps

			# Check if paused and wait for resume
			if self._paused.get(session_id, False):
				self._resume_events[session_id].clear()
				await on_event({
					"type": "paused",
					"reason": "awaiting_user",
					"step": step_count,
				})
				await self._resume_events[session_id].wait()
				await on_event({
					"type": "resumed",
					"step": step_count,
				})

			await on_event({
				"type": "step_start",
				"step": step_count,
			})

		async def on_step_end(agent_instance: Agent) -> None:
			"""Callback called after each step."""
			nonlocal step_count
			step_count = agent_instance.state.n_steps

			# Report action results from history
			if agent_instance.history and agent_instance.history.history:
				last_item = agent_instance.history.history[-1]
				if last_item.result:
					for result in last_item.result:
						if result.error:
							await on_event({
								"type": "error",
								"message": result.error,
								"step": step_count,
							})
						elif result.extracted_content:
							await on_event({
								"type": "message",
								"content": result.extracted_content,
								"step": step_count,
							})

			# Report browser state after step
			state = await browser_service.get_state(session_id)
			await on_event({
				"type": "browser_state",
				"step": step_count,
				**state,
			})

		try:
			history = await agent.run(
				max_steps=max_steps,
				on_step_start=on_step_start,
				on_step_end=on_step_end,
			)

			# Report final result
			if history:
				final_result = history.final_result()
				if final_result:
					await on_event({
						"type": "message",
						"content": str(final_result),
						"role": "ai",
					})

		except Exception as e:
			await on_event({
				"type": "error",
				"message": str(e),
				"step": step_count,
			})
		finally:
			await on_event({"type": "done", "step": step_count})

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