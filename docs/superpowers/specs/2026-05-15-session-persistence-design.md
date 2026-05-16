# 历史会话持久化与恢复设计

**日期：** 2026-05-15

## 目标

实现数据持久化存储和历史会话消息展示。点击历史会话时，能展示历史对话内容、历史截图，并支持继续对话。

## 当前架构分析

- **前端：** `CopilotChat` (CopilotKit) 通过 HttpAgent 连接后端 `/agui` 端点
- **后端：** `agent_service` 管理 Agent 生命周期，`browser_service` 管理浏览器状态
- **问题：** 消息和浏览器快照存在内存中，服务重启丢失；Agent 每次都是新建，无法恢复历史上下文

## 数据模型变更

### 新增表：`agent_messages`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID7 |
| session_id | TEXT FK | 关联 sessions |
| role | TEXT | "user" / "assistant" |
| content | TEXT | 消息文本内容 |
| attachments | TEXT JSON | 附件列表（预留） |
| created_at | DATETIME | 创建时间 |

### 扩展表：`browser_states`

| 字段 | 类型 | 说明 |
|------|------|------|
| history | TEXT JSON | 历史快照数组（每个快照含 url、tabs、screenshot） |
| updated_at | DATETIME | 更新时间 |

## 后端改动

### 1. `session_service.py` — 新增方法

```python
async def add_message(session_id: str, role: str, content: str,
                      attachments: str = "[]") -> Message
async def get_agent_messages(session_id: str) -> list[Message]
async def save_browser_history(session_id: str, history: list[dict])
async def get_browser_history(session_id: str) -> list[dict]
```

### 2. `agent_service.py` — 修改 run_agent

```python
async def run_agent(
    session_id: str,
    message: str,
    on_event: Callable,
    max_steps: int = 100,
):
    # 在 on_step_end callback 中：
    # 1. 将 user/assistant 消息持久化到 agent_messages
    # 2. 将浏览器快照追加到 browser_states.history
```

### 3. `agui.py` — 新增 /connect 端点

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

1. 数据库迁移：新增 `agent_messages` 表，扩展 `browser_states`
2. `session_service` 新增消息读写方法
3. `agent_service` 修改：在 callback 中持久化消息和快照
4. `agui.py` 新增 `/connect` 端点
5. 前端 CopilotKit 配置确认（应无需改动）