"""
单元测试: 数据持久化与历史展示功能

测试内容:
1. SQLite 数据库初始化与表结构自适应迁移
2. SessionService 数据操作 (会话、消息、网页快照)
3. 级联删除 (删除会话时物理清理关联的所有数据)
4. 历史状态获取端点 GET /api/sessions/{session_id}/browser_states
"""
import sys
from pathlib import Path

import pytest

# 添加 backend 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config
from app.db.database import get_db, init_db
from app.services.session_service import session_service
from app.utils import uuid7str

# ============================================================================
# 测试夹具 (Fixtures)
# ============================================================================

@pytest.fixture(autouse=True)
async def setup_test_db(tmp_path):
    """每个测试使用独立的临时数据库"""
    test_db_path = tmp_path / "test_workspace.db"
    original_db_path = Config.DATABASE_PATH
    Config.DATABASE_PATH = test_db_path
    
    # 初始化数据库
    await init_db()
    
    yield
    
    # 恢复原数据库路径
    Config.DATABASE_PATH = original_db_path


# ============================================================================
# 测试用例
# ============================================================================

@pytest.mark.asyncio
async def test_database_schema_initialization():
    """测试数据库初始化和升级，确认表和索引正确创建"""
    conn = await get_db()
    try:
        # 1. 验证表是否存在
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = [row[0] for row in await cursor.fetchall()]
            assert "sessions" in tables
            assert "messages" in tables
            assert "browser_states" in tables

        # 2. 验证 browser_states 字段结构包含 'id'
        async with conn.execute("PRAGMA table_info(browser_states)") as cursor:
            columns = {row["name"]: row for row in await cursor.fetchall()}
            assert "id" in columns
            assert "session_id" in columns
            assert "url" in columns
            assert "screenshot" in columns
            assert "created_at" in columns
            
            # id 列应当是主键
            assert columns["id"]["pk"] == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_database_initialization_uses_canonical_schema_file(tmp_path):
    """Database initialization should load the shared SQL schema file."""
    from app.db import database

    assert database.SCHEMA_PATH.exists()
    schema_sql = database.load_schema_sql()
    assert "CREATE TABLE IF NOT EXISTS test_runs" in schema_sql

    original_db_path = Config.DATABASE_PATH
    Config.DATABASE_PATH = tmp_path / "canonical_schema.db"
    try:
        await init_db()
        assert Config.DATABASE_PATH.exists()
        conn = await get_db()
        try:
            async with conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_replays'"
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
        finally:
            await conn.close()
    finally:
        Config.DATABASE_PATH = original_db_path


@pytest.mark.asyncio
async def test_session_creation_with_defined_id():
    """测试支持传入预定义 ID 创建会话"""
    custom_id = uuid7str()
    session = await session_service.create_session(
        title="Custom ID Session", session_id=custom_id
    )
    assert session.id == custom_id
    assert session.title == "Custom ID Session"
    
    # 验证是否写入数据库
    db_session = await session_service.get_session(custom_id)
    assert db_session is not None
    assert db_session.title == "Custom ID Session"


@pytest.mark.asyncio
async def test_messages_persistence():
    """测试消息 (Messages) 持久化存储与正序读取"""
    session_id = uuid7str()
    await session_service.create_session(title="Messages Test", session_id=session_id)
    
    # 添加用户消息和助理消息
    msg1 = await session_service.add_message(session_id, "user", "How is weather?")
    msg2 = await session_service.add_message(session_id, "assistant", "Sunny!")
    
    assert msg1.role == "user"
    assert msg2.role == "assistant"
    
    # 验证读取排序
    msgs = await session_service.get_messages(session_id)
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "How is weather?"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "Sunny!"


@pytest.mark.asyncio
async def test_browser_states_persistence_and_multi_rows():
    """测试一个会话保存多行历史浏览器快照"""
    session_id = uuid7str()
    await session_service.create_session(title="Snapshot Test", session_id=session_id)
    
    # 持久化第 1 帧
    state1 = await session_service.add_browser_state(
        session_id=session_id,
        url="https://google.com",
        title="Google",
        screenshot="base64_google_screenshot"
    )
    
    # 持久化第 2 帧
    state2 = await session_service.add_browser_state(
        session_id=session_id,
        url="https://github.com",
        title="GitHub",
        screenshot="base64_github_screenshot"
    )
    
    assert state1["url"] == "https://google.com"
    assert state2["url"] == "https://github.com"
    
    # 验证读取
    states = await session_service.get_browser_states(session_id)
    assert len(states) == 2
    assert states[0]["url"] == "https://google.com"
    assert states[0]["screenshot"] == "base64_google_screenshot"
    assert states[1]["url"] == "https://github.com"
    assert states[1]["screenshot"] == "base64_github_screenshot"


@pytest.mark.asyncio
async def test_cascade_deletion():
    """测试在删除会话时级联删除消息和快照"""
    session_id = uuid7str()
    await session_service.create_session(title="Cascade Test", session_id=session_id)
    
    await session_service.add_message(session_id, "user", "Message content")
    await session_service.add_browser_state(
        session_id=session_id,
        url="https://test.com",
        title="Test",
        screenshot="screenshot_data"
    )
    
    # 验证存在
    msgs = await session_service.get_messages(session_id)
    states = await session_service.get_browser_states(session_id)
    assert len(msgs) == 1
    assert len(states) == 1
    
    # 删除会话
    success = await session_service.delete_session(session_id)
    assert success is True
    
    # 验证全部物理删除干净
    db_session = await session_service.get_session(session_id)
    assert db_session is None
    
    msgs_after = await session_service.get_messages(session_id)
    states_after = await session_service.get_browser_states(session_id)
    assert len(msgs_after) == 0
    assert len(states_after) == 0


@pytest.mark.asyncio
async def test_get_browser_states_api_endpoint():
    """测试获取历史网页快照的 API 端点"""
    session_id = uuid7str()
    await session_service.create_session(title="API Test", session_id=session_id)
    
    await session_service.add_browser_state(
        session_id=session_id,
        url="https://api-test.org",
        title="API Test Title",
        screenshot="api_screenshot"
    )
    
    # 模拟 API 路由调用
    from app.api.sessions import get_browser_states
    response = await get_browser_states(session_id)
    
    assert isinstance(response, list)
    assert len(response) == 1
    assert response[0]["url"] == "https://api-test.org"
    assert response[0]["title"] == "API Test Title"
    assert response[0]["screenshot"] == "api_screenshot"
