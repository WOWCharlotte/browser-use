# 编码报告: feat-persistence_and_history-20260520

## 编码阶段总结

### 完成时间
2026-05-20

### 实现与修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/db/database.py` | 修改 | 重构 `browser_states` 表结构，加入独立 UUID 主键并添加会话索引 |
| `backend/app/services/session_service.py` | 修改 | `create_session` 支持预定义 ID；增加 `add_browser_state` 和 `get_browser_states` 服务函数 |
| `backend/app/services/agent_service.py` | 修改 | 在 `on_step_end` 期间持久化每步的助手消息和网页快照截图；在 run 结尾保存最终助手消息 |
| `backend/app/api/agui.py` | 修改 | `/api/agui` 请求进入时，校验会话是否存在、自动创建/更新会话，并将用户提问持久化到 messages 表 |
| `backend/app/api/sessions.py` | 修改 | 暴露新端点 `GET /api/sessions/{session_id}/browser_states` 用于前端获取历史状态快照列表 |
| `frontend/src/lib/api.ts` | 修改 | 新增 `fetchBrowserStates` 接口请求方法 |
| `frontend/src/components/chat/ChatWindow.tsx` | 修改 | 在 `sessionId` 切换时，自动拉取后端历史消息并灌入 CopilotKit 实例的 `agent.setMessages` 重新渲染 |
| `frontend/src/hooks/useStateSnapshot.ts` | 修改 | 修复 Agent 实例切换时 local state 未重置的问题，确保 hook 的 `history` 切换时立即清空 |
| `frontend/src/app/page.tsx` | 修改 | 整合历史数据拉取与 Live Snapshot 合并逻辑，支持平滑的会话切换、自动播放历史截图和 live 增量去重合并 |

---

## Task 1: 后端数据库重构与服务扩展

### backend/app/db/database.py
**修改内容**:
- `init_db()` 加入 `PRAGMA table_info` 数据库表字段动态查询。
- 自适应升级：若检测到旧 `browser_states` 表没有主键 `id` 列，则 DROP 并重建，防止开发期间旧结构冲突。
- 在 `browser_states` 中设立独立主键 `id` 和外键 `session_id`。
- 新增 `idx_browser_states_session_id` 和 `idx_messages_session_id` 索引，提升历史读取速度。

### backend/app/services/session_service.py
**修改内容**:
- `create_session` 函数扩展，支持 `session_id` 参数（对于前端自动生成的 uuid7 标识，无需在数据库再次更换 ID）。
- 编写 `add_browser_state(session_id, url, title, screenshot)` 方法，安全追加网页截图数据。
- 编写 `get_browser_states(session_id)` 方法，按时间升序返回所有网页快照属性（url, title, screenshot）。

---

## Task 2: 后端消息与截图的实时持久化拦截

### backend/app/api/agui.py
**修改内容**:
- 用户提问发送到 `/api/agui` 时：
  - 自动调用 `get_session` 校验会话是否存在；如果不存在，则以当前提问作为标题自动新建该 `session_id`。
  - 如果会话标题为默认 "New conversation"，则自动用用户提问的前 30 个字重命名会话标题。
  - 调用 `add_message` 持久化提问消息（带去重过滤保障防重复触发）。

### backend/app/services/agent_service.py
**修改内容**:
- 在核心 `on_step_end` 钩子中：
  - 将当前步产生的 `thinking`、`memory`、`next_goal` 等助理的思考数据聚合成一个 unified text，并调用 `add_message` 持久化。
  - 调用 `add_browser_state` 将当前步的 url、title、screenshot 写入数据库。
- 在 `run_agent` 执行终点：
  - 若产生了 `final_result` 结果，同样持久化一条 assistant 消息。
- 所有数据持久化逻辑均用 `try-except` 隔离，保障即使数据库写入失败也不会对 Agent 本身的运转流程带来任何干扰。

---

## Task 3: 后端历史数据读取 API 暴露

### backend/app/api/sessions.py
**修改内容**:
- 新增 `GET /sessions/{session_id}/browser_states` 路由，直接调用 service 中的 `get_browser_states` 函数获取序列化快照列表。

---

## Task 4: 前端接口与历史数据重载实现

### frontend/src/lib/api.ts
**修改内容**:
- 定义并导出了 `fetchBrowserStates(sessionId)` 方法。

### frontend/src/components/chat/ChatWindow.tsx
**修改内容**:
- 引用 CopilotKit v2 的 `useAgent` hook 捕获 `agent` 实例。
- 监听 `sessionId` 更改，通过异步 `getMessages(sessionId)` 加载历史，将角色转换为 CopilotKit 官方的 `"user" | "assistant"` 并调用 `agent.setMessages(...)` 实现一键重载渲染。

### frontend/src/hooks/useStateSnapshot.ts
**修改内容**:
- 修复了原始 Hook 不会在 Agent 上下文更改时清空 history 的 Bug。添加了对 `[agent]` 变量的重置 Effect，保证切换侧边栏时前一会话的截图状态被立即释放。

### frontend/src/app/page.tsx
**修改内容**:
- 设立 `combinedHistory` 本地组件状态。
- 在 `currentSessionId` 改变时，立即将状态清空，并异步拉取 `fetchBrowserStates` 进行初始化填充，设置最新图片指针。
- 在 Agent 实时运行产生新 `history` 更改时，与已有 `combinedHistory` 按照 URL/Title/Screenshot 进行去重和增量追加，并自动滚动选中最新一帧。

---

## 待完成

| 任务 | 状态 | 说明 |
|------|------|------|
| 阶段 4: 编码评审 | ⏳ 进行中 | 即将输出 code_review_v1.md 评审文件 |
| 阶段 5: 单元测试编写 | ⏳ 待进行 | 待编写与持久化相关的测试用例 |

---

## 版本记录

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1 | 2026-05-20 | 初始数据持久化与历史展示功能编码实现 |
