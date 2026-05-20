import json
from datetime import datetime
from typing import Optional

from app.db.database import get_db
from app.models.message import Attachment, Message
from app.models.session import Session
from app.utils import uuid7str


def _row_to_dict(row) -> dict:
	"""Convert aiosqlite.Row to dict properly."""
	# sqlite3.Row and aiosqlite.Row both support direct dict() conversion via keys()
	return dict(zip(row.keys(), row))


class SessionService:
	async def list_sessions(self) -> list[Session]:
		db = await get_db()
		try:
			cursor = await db.execute('SELECT * FROM sessions ORDER BY updated_at DESC')
			rows = await cursor.fetchall()
			return [Session(**_row_to_dict(row)) for row in rows]
		finally:
			await db.close()

	async def get_session(self, session_id: str) -> Optional[Session]:
		db = await get_db()
		try:
			cursor = await db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
			row = await cursor.fetchone()
			return Session(**_row_to_dict(row)) if row else None
		finally:
			await db.close()

	async def create_session(self, title: str = 'New conversation', session_id: Optional[str] = None) -> Session:
		session = Session(id=session_id or uuid7str(), title=title)
		db = await get_db()
		try:
			await db.execute(
				'INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
				(session.id, session.title, session.created_at.isoformat(), session.updated_at.isoformat()),
			)
			await db.commit()
		finally:
			await db.close()
		return session

	async def update_session(self, session_id: str, title: str) -> Optional[Session]:
		now = datetime.now().isoformat()
		db = await get_db()
		try:
			await db.execute('UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?', (title, now, session_id))
			await db.commit()
		finally:
			await db.close()
		return await self.get_session(session_id)

	async def delete_session(self, session_id: str) -> bool:
		db = await get_db()
		try:
			await db.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
			await db.execute('DELETE FROM browser_states WHERE session_id = ?', (session_id,))
			result = await db.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
			await db.commit()
			return result.rowcount > 0
		finally:
			await db.close()

	async def get_messages(self, session_id: str) -> list[Message]:
		db = await get_db()
		try:
			cursor = await db.execute('SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC', (session_id,))
			rows = await cursor.fetchall()
			messages = []
			for row in rows:
				d = _row_to_dict(row)
				if 'attachments' in d and isinstance(d['attachments'], str):
					d['attachments'] = json.loads(d['attachments'])
				messages.append(Message(**d))
			return messages
		finally:
			await db.close()

	async def add_message(self, session_id: str, role: str, content: str, attachments: str = '[]') -> Message:
		message = Message(
			id=uuid7str(),
			session_id=session_id,
			role=role,
			content=content,
			attachments=[],
		)
		if attachments:
			message.attachments = [Attachment(**a) for a in json.loads(attachments)]
		att_json = json.dumps([a.model_dump() for a in message.attachments]) if message.attachments else '[]'
		db = await get_db()
		try:
			await db.execute(
				'INSERT INTO messages (id, session_id, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?, ?)',
				(message.id, message.session_id, message.role, message.content, att_json, message.created_at.isoformat()),
			)
			await db.commit()
		finally:
			await db.close()
		return message

	async def add_browser_state(
		self, session_id: str, url: Optional[str], title: Optional[str], screenshot: Optional[str]
	) -> dict:
		state_id = uuid7str()
		now = datetime.now().isoformat()
		db = await get_db()
		try:
			await db.execute(
				'INSERT INTO browser_states (id, session_id, url, title, screenshot, created_at) VALUES (?, ?, ?, ?, ?, ?)',
				(state_id, session_id, url, title, screenshot, now),
			)
			await db.commit()
		finally:
			await db.close()
		return {'id': state_id, 'session_id': session_id, 'url': url, 'title': title, 'screenshot': screenshot, 'created_at': now}

	async def get_browser_states(self, session_id: str) -> list[dict]:
		db = await get_db()
		try:
			cursor = await db.execute(
				'SELECT url, title, screenshot FROM browser_states WHERE session_id = ? ORDER BY created_at ASC', (session_id,)
			)
			rows = await cursor.fetchall()
			return [_row_to_dict(row) for row in rows]
		finally:
			await db.close()


session_service = SessionService()
