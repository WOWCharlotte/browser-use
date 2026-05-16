# 历史会话持久化与恢复设计

**日期：** 2026-05-15

## 目标

实现数据持久化存储和历史会话消息展示。点击历史会话时，能展示历史对话内容、历史截图，并支持继续对话。

## 当前架构分析

- **前端：** `CopilotChat` (CopilotKit) 通过 HttpAgent 连接后端 `/api/agui` 端点
- **后端：** `agent_service` 管理 Agent 生命周期，`browser_service` 管理 BrowserSession
- **现有基础设施：**
  - `messages` 表已有，`session_service.add_message()` 已实现
  - `browser_states` 表有 url/title/screenshot，缺少 `history` 字段
  - `agent_service._history` 存在内存，重启丢失

- **问题：**
  - 消息未持久化（每次 run_agent 都是新 Agent）
  - 浏览器快照只在内存的 `_history` 中
  - 缺少 `/connect` 端点恢复历史会话

## 数据模型变更

### 扩展表：`messages`（已有）

继续使用现有 `messages` 表，role 值为 "user" / "assistant"。

### 扩展表：`browser_states`（已有）

新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| history | TEXT JSON | 历史快照数组（每个快照含 url、tabs、screenshot） |

### 数据库迁移

```sql
ALTER TABLE browser_states ADD COLUMN history TEXT DEFAULT '[]';
```

## 后端改动

### 1. `database.py` — 数据库初始化更新

```python
# 在 init_db() 中，browser_states 表已创建时添加 history 字段
# 需要处理已有数据的迁移
```

### 2. `session_service.py` — 新增/修改方法

```python
# 已存在：add_message() - 可直接使用
# 新增：
async def get_agent_messages(session_id: str) -> list[Message]
async def save_browser_history(session_id: str, history: list[dict])
async def get_browser_history(session_id: str) -> list[dict]
```

### 3. `agent_service.py` — 修改 run_agent

```python
# 在 on_step_end callback 中：
# 1. 调用 session_service.add_message() 保存 assistant 消息
# 2. 调用 session_service.save_browser_history() 持久化浏览器历史
```

### 4. `agui.py` — 新增 /connect 端点

```python
@router.post("/agent/{agentId}/connect")
async def connect_agent(input_data: RunAgentInput, request: Request):
    # 1. 从 DB 加载历史消息 + 浏览器状态
    # 2. 恢复 browser_service 状态
    # 3. SSE 返回 RUN_STARTED + 历史消息事件
    # 4. 返回 RUN_FINISHED（connect 本身不执行任务）
```

## 事件流

### 创建新会话时

```
用户发送消息 → onSubmitInput → copilotkit.runAgent
                                          ↓
前端 /agui 端点 → agent_service.run_agent → 执行任务
                                          ↓
on_step_end callback → 保存消息到 DB + 快照到 browser_states
```

### 恢复历史会话时

```
用户点击会话 → CopilotChat 传入 threadId → 调用 /connect
                                        ↓
后端从 DB 加载消息 + 浏览器状态
浏览器状态恢复到 browser_service
SSE 返回历史消息事件
前端 CopilotKit 注入历史消息
用户继续对话
```

## 已知限制

- Agent 无法看到之前 tool call 的详细结果
- 但可看到最终状态（页面 URL、tabs、截图），大多数场景足够

## 实现顺序

1. 数据库迁移：`browser_states` 表添加 `history` 字段
2. `session_service` 新增 `save_browser_history` / `get_browser_history` 方法
3. `agent_service` 修改：在 `on_step_end` 中调用持久化方法
4. `agui.py` 新增 `/agent/{agentId}/connect` 端点
5. 前端 CopilotKit 配置确认（应无需改动）