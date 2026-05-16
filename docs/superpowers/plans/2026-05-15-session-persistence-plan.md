# 历史会话持久化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现数据持久化存储和历史会话消息展示，点击历史会话时能展示历史对话内容和截图，并支持继续对话。

**Architecture:** 复用现有 `messages` 表存储对话，扩展 `browser_states` 表存储历史快照，新增 `/connect` 端点恢复会话。

**Tech Stack:** Python 3.11+, FastAPI, aiosqlite, browser-use

---

## 文件结构

```
backend/app/
├── db/database.py          # 数据库初始化/迁移
├── services/
│   ├── session_service.py  # 新增 history 方法
│   └── agent_service.py    # 持久化消息和快照
└── api/
    └── agui.py             # 新增 /connect 端点
```

---

## Task 1: 数据库迁移 — 添加 history 字段

**Files:**
- Modify: `backend/app/db/database.py:16-44`

- [ ] **Step 1: 修改 init_db 中的 browser_states 表创建语句**

在 `init_db()` 函数里，找到 `CREATE TABLE IF NOT EXISTS browser_states` 语句，在 `screenshot TEXT` 后添加 `history TEXT DEFAULT '[]'`。

原始代码 (line 35-43):
```python
CREATE TABLE IF NOT EXISTS browser_states (
    session_id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    screenshot TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

修改为:
```python
CREATE TABLE IF NOT EXISTS browser_states (
    session_id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    screenshot TEXT,
    history TEXT DEFAULT '[]',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

- [ ] **Step 2: 运行验证**

Run: `cd backend && uv run python -c "import asyncio; from app.db.database import init_db; asyncio.run(init_db()); print('DB init OK')"`
Expected: DB init OK（无报错）

- [ ] **Step 3: 提交**

```bash
git add backend/app/db/database.py
git commit -m "feat(backend): 添加 browser_states.history 字段

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: session_service 新增 history 方法

**Files:**
- Modify: `backend/app/services/session_service.py`

- [ ] **Step 1: 添加 save_browser_history 方法**

在 `SessionService` 类中添加：

```python
async def save_browser_history(self, session_id: str, history: list[dict]) -> None:
    """保存浏览器历史快照"""
    import json
    db = await get_db()
    try:
        await db.execute(
            "UPDATE browser_states SET history = ?, updated_at = ? WHERE session_id = ?",
            (json.dumps(history), datetime.now().isoformat(), session_id)
        )
        await db.commit()
    finally:
        await db.close()
```

- [ ] **Step 2: 添加 get_browser_history 方法**

在 `SessionService` 类中添加：

```python
async def get_browser_history(self, session_id: str) -> list[dict]:
    """获取浏览器历史快照"""
    import json
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT history FROM browser_states WHERE session_id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        if row:
            history_data = row["history"] if row["history"] else "[]"
            return json.loads(history_data)
        return []
    finally:
        await db.close()
```

- [ ] **Step 3: 添加 update_browser_state 方法**

在 `SessionService` 类中添加（用于创建或更新 browser_states 记录）：

```python
async def update_browser_state(self, session_id: str, url: str = "", title: str = "", screenshot: str = "", history: list[dict] | None = None) -> None:
    """创建或更新浏览器状态"""
    import json
    db = await get_db()
    try:
        history_json = json.dumps(history) if history is not None else "[]"
        await db.execute(
            """INSERT INTO browser_states (session_id, url, title, screenshot, history, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
               url = excluded.url, title = excluded.title, screenshot = excluded.screenshot,
               history = excluded.history, updated_at = excluded.updated_at""",
            (session_id, url, title, screenshot, history_json, datetime.now().isoformat())
        )
        await db.commit()
    finally:
        await db.close()
```

- [ ] **Step 4: 验证导入无误**

Run: `cd backend && uv run python -c "from app.services.session_service import session_service; print('OK')"`
Expected: OK

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/session_service.py
git commit -m "feat(backend): session_service 添加浏览器历史持久化方法

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: agent_service 持久化消息和快照

**Files:**
- Modify: `backend/app/services/agent_service.py`

- [ ] **Step 1: 在 run_agent 开始时保存 user 消息**

在 `run_agent` 方法中，用户消息发送时（line 316-327 的 `agent.addMessage` 之后），添加：

```python
# 保存用户消息到数据库
await session_service.add_message(
    session_id=session_id,
    role="user",
    content=value if isinstance(value, str) else value.get("text", "")
)
```

具体位置在 line 329 `setInputValue("")` 之前。

- [ ] **Step 2: 在 on_step_end 中保存 assistant 消息**

在 `on_step_end` 函数中（line 177-181 的 `TEXT_MESSAGE_END` 发送之后），添加：

```python
# 保存 assistant 消息到数据库
if parts or last_item.result:
    content = "\n".join(parts) if parts else ""
    if last_item.result:
        for result in last_item.result:
            if result.extracted_content:
                content = result.extracted_content
                break
    if content:
        await session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=content
        )
```

- [ ] **Step 3: 在 on_step_end 中保存浏览器快照**

在 line 213 `await on_event({"type": EVENT_STATE_SNAPSHOT, ...})` 之后，添加：

```python
# 持久化浏览器历史到数据库
history_to_save = list(self._history[session_id])
await session_service.save_browser_history(session_id, history_to_save)
```

- [ ] **Step 4: 确保 session_service 已导入**

检查文件顶部 `from app.services.session_service import session_service` 是否存在，如不存在则添加。

- [ ] **Step 5: 运行验证**

Run: `cd backend && uv run python -c "from app.services.agent_service import agent_service; print('OK')"`
Expected: OK

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/agent_service.py
git commit -m "feat(backend): agent_service 持久化消息和浏览器快照到数据库

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: agui.py 新增 /connect 端点

**Files:**
- Modify: `backend/app/api/agui.py`

- [ ] **Step 1: 添加 connect 端点**

在 `agui.py` 文件末尾（`return StreamingResponse(...)` 之后），添加新的路由：

```python
@router.post("/agent/{agentId}/connect")
async def connect_agent(request: Request, agentId: str) -> StreamingResponse:
    """
    AG-UI Protocol Connect Endpoint

    恢复已有线程的历史消息和浏览器状态。
    """
    from app.services.session_service import session_service

    # 从 request body 解析 thread_id
    body = await request.json()
    thread_id = body.get("threadId") or body.get("thread_id")
    if not thread_id:
        from app.utils import uuid7str
        thread_id = uuid7str()

    accept_header = request.headers.get("accept", "text/event-stream")
    encoder = EventEncoder(accept=accept_header)

    async def event_generator() -> AsyncGenerator[str, None]:
        from ag_ui.core import (
            EventType,
            RunStartedEvent,
            RunFinishedEvent,
            TextMessageStartEvent,
            TextMessageContentEvent,
            TextMessageEndEvent,
            StateSnapshotEvent,
        )
        from app.utils import uuid7str

        # 发送 RUN_STARTED
        run_id = uuid7str()
        yield encoder.encode(RunStartedEvent(thread_id=thread_id, run_id=run_id))

        # 加载历史消息
        messages = await session_service.get_messages(thread_id)
        for msg in messages:
            msg_id = msg.id if hasattr(msg, 'id') else str(msg.get('id', ''))
            role = msg.role if hasattr(msg, 'role') else str(msg.get('role', 'assistant'))
            content = msg.content if hasattr(msg, 'content') else str(msg.get('content', ''))

            yield encoder.encode(TextMessageStartEvent(
                message_id=msg_id,
                role=role,
            ))
            yield encoder.encode(TextMessageContentEvent(
                message_id=msg_id,
                delta=content,
            ))
            yield encoder.encode(TextMessageEndEvent(
                message_id=msg_id,
            ))

        # 加载并恢复浏览器状态
        from app.services.browser_service import browser_service
        history = await session_service.get_browser_history(thread_id)
        if history:
            latest = history[-1]
            # 恢复浏览器状态到 browser_service
            if thread_id not in browser_service._sessions:
                await browser_service.create_session(thread_id)

            # 发送最后的状态快照
            yield encoder.encode(StateSnapshotEvent(
                snapshot=latest,
            ))

        # 发送 RUN_FINISHED
        yield encoder.encode(RunFinishedEvent(
            thread_id=thread_id,
            run_id=run_id,
            result={"outcome": "restored"},
        ))

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: 确保 AsyncGenerator 导入**

检查文件顶部 `from typing import Any, AsyncGenerator, List` 是否已存在，如没有则添加到导入。

- [ ] **Step 3: 运行验证**

Run: `cd backend && uv run python -c "from app.api.agui import router; print('OK')"`
Expected: OK

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/agui.py
git commit -m "feat(backend): 添加 /connect 端点恢复历史会话

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: 验证测试

**Files:**
- Modify: `backend/tests/test_persistence.py` (新建)

- [ ] **Step 1: 创建集成测试**

创建 `backend/tests/test_persistence.py`：

```python
import pytest
import asyncio
from app.services.session_service import session_service
from app.db.database import init_db, get_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield

@pytest.mark.asyncio
async def test_save_and_get_browser_history():
    session_id = "test-session-1"
    history = [
        {"url": "https://example.com", "title": "Example", "screenshot": "base64..."},
        {"url": "https://example.com/page2", "title": "Page 2", "screenshot": "base64..."},
    ]

    # 先创建 session
    await session_service.create_session("Test Session")

    # 保存历史
    await session_service.update_browser_state(session_id, history=history)

    # 获取历史
    retrieved = await session_service.get_browser_history(session_id)

    assert len(retrieved) == 2
    assert retrieved[0]["url"] == "https://example.com"

@pytest.mark.asyncio
async def test_message_persistence():
    session_id = "test-session-2"
    await session_service.create_session("Test Session 2")

    # 添加消息
    msg = await session_service.add_message(session_id, "user", "Hello")
    assert msg.id is not None

    # 获取消息
    messages = await session_service.get_messages(session_id)
    assert len(messages) >= 1
    assert any(m.content == "Hello" for m in messages)
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && uv run pytest tests/test_persistence.py -v`
Expected: 2 passed

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_persistence.py
git commit -m "test(backend): 添加会话持久化集成测试

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 实现顺序

1. Task 1: 数据库迁移
2. Task 2: session_service 新增方法
3. Task 3: agent_service 持久化
4. Task 4: agui.py /connect 端点
5. Task 5: 验证测试

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-15-session-persistence-plan.md`**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?