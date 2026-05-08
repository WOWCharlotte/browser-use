"""
Interruptible Agent Example

Demonstrates how to create an agent that can be interrupted via terminal commands
(/pause, /resume).

Usage:
    python examples/interrupt.py

Commands while running:
    /pause  - Pause the agent
    /resume - Resume the agent
    /stop   - Stop the agent
    Ctrl+C  - Stop the agent
"""

import asyncio
import hashlib
import os
import sys
import threading
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Optional lmnr tracing (same pattern as examples/models/qwen.py)
project_api_key = os.getenv('LMNR_PROJECT_API_KEY')
if project_api_key:
	from lmnr import Laminar

	Laminar.initialize(project_api_key=project_api_key)

from browser_use import Agent


# --- Interrupt controller ---

# Late binding for agent reference in stdin thread
agent_ref: Optional[Agent] = None


class InterruptController:
	"""Manages pause/resume interrupts via stdin and QR/captcha detection."""

	def __init__(self):
		self._paused: bool = False
		self._awaiting_resume: bool = False
		self._resume_event: asyncio.Event = asyncio.Event()
		self._resume_event.set()  # Not blocked initially

	def parse_command(self, line: str) -> Optional[str]:
		"""Parse command from input line. Returns 'pause', 'resume', 'stop', or None."""
		cmd = line.strip().lower()
		if cmd == '/pause':
			return 'pause'
		elif cmd == '/resume':
			return 'resume'
		elif cmd == '/stop':
			return 'stop'
		return None

	async def handle_command(self, cmd: str, agent: Agent) -> None:
		"""Handle a parsed command."""
		global agent_ref
		agent_ref = agent

		if cmd == 'pause':
			if not self._paused:
				self._paused = True
				self._awaiting_resume = True
				agent.pause()
				print('\n⏸️  Agent paused. Type /resume to continue or Ctrl+C to stop.')
		elif cmd == 'resume':
			if self._paused:
				self._paused = False
				self._awaiting_resume = False
				self._resume_event.set()
				agent.resume()
				print('\n▶️  Agent resumed.')
		elif cmd == 'stop':
			self._paused = False
			self._awaiting_resume = False
			self._resume_event.set()
			agent.stop()
			print('\n⏹️  Agent stopped.')


# Global controller instance
controller = InterruptController()


# --- stdin monitoring thread ---


def stdin_monitor(controller: InterruptController, loop: asyncio.AbstractEventLoop):
	"""Background thread that monitors stdin for /pause and /resume commands."""
	try:
		while True:
			line = sys.stdin.readline()
			if not line:
				break
			cmd = controller.parse_command(line)
			if cmd and agent_ref is not None:
				asyncio.run_coroutine_threadsafe(
					controller.handle_command(cmd, agent_ref),
					loop,
				)
	except Exception:
		pass


# --- Hooks ---


async def on_step_start(agent: Agent) -> None:
	"""Hook called before each step. Handles resume blocking."""
	global agent_ref
	agent_ref = agent  # Share agent reference with stdin thread

	# If we're waiting for resume, block here
	if controller._awaiting_resume:
		print('\n⏸️  Waiting for user intervention to complete...')
		await controller._resume_event.wait()
		controller._resume_event.clear()


async def on_step_end(agent: Agent) -> None:
	"""Hook called after each step (required by AgentHookFunc signature)."""
	pass


def compute_task_hash(task: str) -> str:
	"""Compute SHA256 hash from task string, truncated to 16 chars."""
	return hashlib.sha256(task.encode()).hexdigest()[:16]


def save_agent_history(agent: Agent, task: str) -> None:
	"""Save agent history with task-based hash filename."""
	task_hash = compute_task_hash(task)
	agent.save_history(f'task/{task_hash}.json')


# --- Main ---


async def main():
	from browser_use.llm.openai.chat import ChatOpenAI
	api_key = "sk-be41959674154c7890f354538eed65f6"
	base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

	task = '打开Github(https://github.com)搜索browser-use项目，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮，进入项目主页，点击start按钮。'

	llm = ChatOpenAI(model='qwen-vl-max', api_key=api_key, base_url=base_url)


	agent = Agent(
		task=task,
		llm=llm,
		use_vision=True,
		max_actions_per_step=1,
	)

	# Share agent reference with stdin thread BEFORE starting monitor
	global agent_ref
	agent_ref = agent

	# Start stdin monitor thread
	loop = asyncio.get_event_loop()
	monitor_thread = threading.Thread(
		target=stdin_monitor,
		args=(controller, loop),
		daemon=True,
		name='stdin-monitor',
	)
	monitor_thread.start()

	print('=' * 60)
	print('Interruptible Agent Demo')
	print('Commands:')
	print('  /pause  - Pause the agent')
	print('  /resume - Resume the agent')
	print('  /stop   - Stop the agent')
	print('  Ctrl+C  - Stop the agent')
	print('=' * 60)
	print()

	# Run agent (hooks handle interruptions)
	try:
		await agent.run(on_step_start=on_step_start, on_step_end=on_step_end)
	finally:
		save_agent_history(agent, task)


if __name__ == '__main__':
	asyncio.run(main())
