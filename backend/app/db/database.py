from pathlib import Path

import aiosqlite

from app.config import Config

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DB_PATH = Config.DATABASE_PATH
_DEFAULT_DB_PATH_AT_IMPORT = DB_PATH


def get_db_path() -> Path:
	"""Return the current configured database path."""
	if DB_PATH != _DEFAULT_DB_PATH_AT_IMPORT:
		return Path(DB_PATH)
	return Config.DATABASE_PATH


def load_schema_sql() -> str:
	"""Load the canonical database schema SQL."""
	return SCHEMA_PATH.read_text(encoding="utf-8")


async def get_db() -> aiosqlite.Connection:
	"""Return a database connection as an async context manager."""
	db_path = get_db_path()
	db_path.parent.mkdir(parents=True, exist_ok=True)
	conn = await aiosqlite.connect(db_path, check_same_thread=False)
	conn.row_factory = aiosqlite.Row
	await conn.execute("PRAGMA foreign_keys = ON")
	return conn


async def _drop_legacy_browser_states_if_needed(conn: aiosqlite.Connection) -> None:
	"""Drop old browser state table variants that predate the primary key."""
	try:
		async with conn.execute("PRAGMA table_info(browser_states)") as cursor:
			columns = await cursor.fetchall()
	except Exception:
		return

	if columns and not any(col["name"] == "id" for col in columns):
		await conn.execute("DROP TABLE browser_states")
		await conn.commit()


async def init_db() -> None:
	"""Initialize the database with all required tables."""
	conn = await get_db()
	try:
		await _drop_legacy_browser_states_if_needed(conn)
		await conn.executescript(load_schema_sql())
		await conn.commit()
	finally:
		await conn.close()
