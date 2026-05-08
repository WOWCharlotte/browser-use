import json
from datetime import datetime
from typing import Optional
from app.models.session import Session
from app.models.message import Message, Attachment
from app.db.database import get_db
from app.utils import uuid7str


class SessionService:
	async def list_sessions(self) -> list[Session]:
		async with get_db() as db:
			rows = await db.execute_fetchall(
				"SELECT * FROM sessions ORDER BY updated_at DESC"
			)
			return [Session(**dict(row)) for row in rows]

	async def get_session(self, session_id: str) -> Optional[Session]:
		async with get_db() as db:
			row = await db.execute_fetchone(
				"SELECT * FROM sessions WHERE id = ?", (session_id,)
			)
			return Session(**dict(row)) if row else None

	async def create_session(self, title: str = "New conversation") -> Session:
		session = Session(title=title)
		async with get_db() as db:
			await db.execute(
				"INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
				(session.id, session.title, session.created_at.isoformat(), session.updated_at.isoformat())
			)
			await db.commit()
		return session

	async def update_session(self, session_id: str, title: str) -> Optional[Session]:
		now = datetime.now().isoformat()
		async with get_db() as db:
			await db.execute(
				"UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
				(title, now, session_id)
			)
			await db.commit()
		return await self.get_session(session_id)

	async def delete_session(self, session_id: str) -> bool:
		async with get_db() as db:
			await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
			await db.execute("DELETE FROM browser_states WHERE session_id = ?", (session_id,))
			result = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
			await db.commit()
			return result.rowcount > 0

	async def get_messages(self, session_id: str) -> list[Message]:
		async with get_db() as db:
			rows = await db.execute_fetchall(
				"SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
				(session_id,)
			)
			return [Message(**dict(row)) for row in rows]

	async def add_message(self, session_id: str, role: str, content: str, attachments: str = None) -> Message:
		message = Message(
			id=uuid7str(),
			session_id=session_id,
			role=role,
			content=content,
			attachments=[],
		)
		if attachments:
			message.attachments = [Attachment(**a) for a in json.loads(attachments)]
		att_json = json.dumps([a.model_dump() for a in message.attachments]) if message.attachments else "[]"
		async with get_db() as db:
			await db.execute(
				"INSERT INTO messages (id, session_id, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?, ?)",
				(message.id, message.session_id, message.role, message.content, att_json, message.created_at.isoformat())
			)
			await db.commit()
		return message


session_service = SessionService()