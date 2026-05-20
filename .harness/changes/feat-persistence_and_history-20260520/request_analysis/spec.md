# 需求规格说明书: 数据持久化与历史展示

## 1. 概述

### 1.1 背景
当前 AI Workspace 平台支持多会话管理与实时浏览器运行预览，但缺乏对历史运行记录的持久化和重载功能。重启后端或刷新页面后，历史会话的消息记录和运行中生成的步骤截图无法重新载入，严重影响了用户的使用体验。

### 1.2 目标
1. 保证消息（用户消息和 Agent 助手消息）能够在后台自动写入 SQLite 数据库。
2. 保证浏览器每步的运行状态快照（URL、标题、截图 Base64）能够在后台自动保存到数据库中，且每个会话支持多条历史状态。
3. 实现当用户点击侧边栏的任一会话时，能够无缝重载其所有的历史对话内容和历史截图步骤。

---

## 2. 输入

### 2.1 数据库结构升级

#### sessions 表（保持不变）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 会话 UUID |
| title | TEXT | 会话标题 |

#### messages 表（保持不变）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 消息 UUID |
| session_id | TEXT | 外键关联 sessions.id |
| role | TEXT | 消息发送方 (`"user"` 或 `"assistant"`) |
| content | TEXT | 消息文本内容 |

#### browser_states 表（升级重构：取消 session_id 主键，增加独立主键 id 以支持 1对多 历史）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 状态快照 UUID |
| session_id | TEXT | 外键关联 sessions.id |
| url | TEXT | 网页 URL |
| title | TEXT | 网页标题 |
| screenshot | TEXT | 网页截图 (Base64) |
| created_at | DATETIME | 创建时间，用于正序回放 |

---

## 3. 输出与 API 设计

### 3.1 获取历史截图 API
`GET /api/sessions/{session_id}/browser_states`

#### 响应格式 (JSON Array):
```json
[
  {
    "url": "https://example.com",
    "title": "Example Domain",
    "screenshot": "data:image/png;base64,..."
  }
]
```

### 3.2 前端 API 方法
`fetchBrowserStates(sessionId: string): Promise<BrowserState[]>`

---

## 4. 功能列表

### 4.1 后端功能
- [ ] **数据库自适应升级**：在 `init_db()` 中，若检测到原 `browser_states` 表为旧结构（无 `id` 列），自动 DROP 旧表并以支持历史的多行结构重新建表。
- [ ] **消息写入持久化**：
  - 用户消息：在接收到前端运行请求时自动保存用户 prompt。
  - 助手消息：在 agent `on_step_end` 与最终结果产生时，收集其思考与操作反馈信息并持久化到数据库。
- [ ] **浏览器状态写入持久化**：在 `on_step_end` 期间自动捕获截图和 URL 并入库。
- [ ] **API 暴露**：实现读取特定会话所有历史快照的 HTTP 接口。

### 4.2 前端功能
- [ ] **历史消息动态重载**：在 `ChatWindow.tsx` 中订阅 `sessionId` 的变化，获取历史消息并调用 `agent.setMessages(...)` 更新 CopilotKit 组件的数据。
- [ ] **历史截图播放与 Live 合并**：在 `page.tsx` 中切换会话时自动请求 `fetchBrowserStates` 并将其置为本地 history 状态；当会话处于运行态产生新 live 快照时，无缝合并新旧快照。

---

## 5. 边界条件与异常处理
1. **空会话处理**：点击没有运行过的全新会话时，聊天历史与截图列表全部自动清空，不抛出异常。
2. **重复消息过滤**：在实时运行中，防止 live 产生的截图与本地加载的历史截图产生数据重复。通过在前端进行增量比较去重合并。
3. **大文本截图写入**：对超大 base64 截图，SQLite 具备完美承载力，但需注意在 `delete_session` 中级联删除 `browser_states` 中的所有大图记录，避免数据库膨胀。
