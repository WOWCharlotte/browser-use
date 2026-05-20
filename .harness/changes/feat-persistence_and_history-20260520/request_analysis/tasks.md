# 任务拆分清单: 数据持久化与历史展示

## Task 1: 后端数据库重构与服务扩展

| 字段 | 内容 |
|------|------|
| 目标 | 升级 `browser_states` 表结构以支持历史记录，并提供 CRUD 服务函数 |
| 范围 | 修改 `backend/app/db/database.py`, `backend/app/services/session_service.py` |
| 输入 | `session_id`, `url`, `title`, `screenshot` |
| 输出 | 写入 SQLite 或从 SQLite 读取列表 |
| 验收标准 | 1. 数据库自动删除旧 `browser_states` 表并创建新表。2. `session_service` 提供 `add_browser_state` 和 `get_browser_states` 函数且测试通过。 |
| 依赖 | 无 |
| 优先级 | P0 |

### 子任务
- [ ] 修改 `database.py` 中的 `init_db()` 加入表结构兼容升级逻辑。
- [ ] 在 `session_service.py` 中引入 `add_browser_state` 将截图与 URL 写入数据库。
- [ ] 在 `session_service.py` 中引入 `get_browser_states` 按时间正序查询某个 session 下的所有状态。
- [ ] 确保 `delete_session` 会连带删除 `browser_states` 下所有相关条目。

---

## Task 2: 后端消息与截图的实时持久化拦截

| 字段 | 内容 |
|------|------|
| 目标 | 在 Agent 运行生命周期及 Web 请求中拦截并保存数据 |
| 范围 | 修改 `backend/app/api/agui.py`, `backend/app/services/agent_service.py` |
| 验收标准 | 1. 用户提问被成功存入 `messages`。2. Agent 思考/反馈及最终回答被存入 `messages`。3. 浏览器每步状态被成功存入 `browser_states`。 |
| 依赖 | Task 1 |
| 优先级 | P0 |

### 子任务
- [ ] 修改 `agui.py`，在提取到 `user_message` 启动 run_agent 前，将用户问题存入 `messages`。
- [ ] 修改 `agent_service.py` 的 `on_step_end`，将每步的 url, title, screenshot 保存进数据库。
- [ ] 修改 `agent_service.py` 的 `on_step_end`，累加当步产生的思考、记忆与操作结果并以 `"assistant"` 角色持久化消息。
- [ ] 在 `run_agent` 结尾若有 `final_result` 时存入最终 assistant 消息。

---

## Task 3: 后端历史数据读取 API 暴露

| 字段 | 内容 |
|------|------|
| 目标 | 提供前端获取历史截图的 HTTP 端点 |
| 范围 | 修改 `backend/app/api/sessions.py` |
| 验收标准 | 请求 `GET /api/sessions/{session_id}/browser_states` 返回 JSON 数组，包含每一步的网页信息与 Base64 截图。 |
| 依赖 | Task 1 |
| 优先级 | P0 |

### 子任务
- [ ] 在 `sessions.py` 中新增 `GET /sessions/{session_id}/browser_states` 路由。
- [ ] 调用 `session_service.get_browser_states` 返回序列化后的列表。

---

## Task 4: 前端接口与历史数据重载实现

| 字段 | 内容 |
|------|------|
| 目标 | 前端调用接口、在切换会话时渲染历史对话记录与历史截图 |
| 范围 | 修改 `frontend/src/lib/api.ts`, `frontend/src/components/chat/ChatWindow.tsx`, `frontend/src/app/page.tsx` |
| 验收标准 | 1. 点击会话列表，ChatWindow 立即以历史对话填充（而不是空白或残留上一会话）。2. 浏览器预览立即以历史最后一帧状态填充，并可以通过分页控制回放历史所有截图。3. 运行时产生的新截图和原历史快照安全合并，不会产生重复项。 |
| 依赖 | Task 2, Task 3 |
| 优先级 | P0 |

### 子任务
- [ ] 在 `frontend/src/lib/api.ts` 中定义 `fetchBrowserStates` 接口。
- [ ] 重构 `ChatWindow.tsx`，使用 `useAgent` 监听 `sessionId` 的变更，异步拉取 `/api/sessions/{sessionId}/messages` 并使用 `agent.setMessages` 还原历史消息。
- [ ] 重构 `page.tsx`，监听 `currentSessionId`，在会话更改时异步获取历史 browser states 设为本地 history，并将 `useStateSnapshot()` 产生的 live 新状态增量过滤合并。
