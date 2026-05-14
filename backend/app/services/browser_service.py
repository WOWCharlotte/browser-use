import asyncio
import json
from typing import Any

from pydantic import HttpUrl

from app.config import Config


class BrowserService:
	def __init__(self) -> None:
		self._sessions: dict[str, dict[str, Any]] = {}

	async def create_session(self, session_id: str) -> dict[str, Any]:
		from browser_use.browser.session import BrowserSession
		session = BrowserSession(
			headless=False,
			args=[f"--remote-debugging-port={Config.CDP_PORT}"]
		)
		await session.start()
		self._sessions[session_id] = {"browser": session, "page": None}
		return await self.get_state(session_id)

	async def get_state(self, session_id: str) -> dict[str, Any]:
		if session_id not in self._sessions:
			return {"url": "", "title": "", "screenshot": ""}
		sess = self._sessions[session_id]
		browser = sess["browser"]
		try:
			page = await browser.get_current_page()
			if page is None:
				return {"url": "", "title": "", "screenshot": ""}
			# page.url 是属性，page.title() 和 page.screenshot() 是异步方法
			url = getattr(page, 'url', '') or ''
			if callable(getattr(page, 'title', None)):
				title = await page.title()
			else:
				title = getattr(page, 'title', '') or ''
			if callable(getattr(page, 'screenshot', None)):
				screenshot = await page.screenshot()
			else:
				screenshot = getattr(page, 'screenshot', '') or ''
			return {"url": url, "title": title, "screenshot": screenshot}
		except Exception as e:
			return {"url": "", "title": "", "screenshot": "", "error": str(e)}

	async def execute_action(self, session_id: str, action: str, args: dict[str, Any]) -> dict[str, Any]:
		if session_id not in self._sessions:
			return {"success": False, "error": "Session not found"}
		sess = self._sessions[session_id]
		browser = sess["browser"]
		try:
			page = await browser.get_current_page()
			if action == "navigate":
				url = args.get("url")
				if not url or not isinstance(url, str):
					return {"success": False, "error": "Invalid or missing URL"}
				HttpUrl(url)  # validate URL format
				await page.goto(url)
			elif action == "click":
				selector = args.get("selector")
				if not selector or not isinstance(selector, str) or not selector.strip():
					return {"success": False, "error": "Invalid or empty selector"}
				await page.click(selector)
			elif action == "type":
				selector = args.get("selector")
				if not selector or not isinstance(selector, str) or not selector.strip():
					return {"success": False, "error": "Invalid or empty selector"}
				text = args.get("text")
				if not isinstance(text, str):
					return {"success": False, "error": "Invalid text value"}
				await page.fill(selector, text)
			elif action == "scroll":
				y = args.get("y", 0)
				if not isinstance(y, int) or y < 0:
					return {"success": False, "error": "Invalid y value: must be non-negative integer"}
				await page.evaluate(f"window.scrollTo(0, {y})")
			elif action == "screenshot":
				pass  # handled in get_state
			else:
				return {"success": False, "error": f"Unknown action: {action}"}
			return await self.get_state(session_id)
		except Exception as e:
			return {"success": False, "error": str(e)}

	async def close_session(self, session_id: str) -> None:
		if session_id in self._sessions:
			await self._sessions[session_id]["browser"].stop()
			del self._sessions[session_id]


browser_service = BrowserService()