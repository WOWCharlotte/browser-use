# AI Workspace GUI Agent - 需求规格说明书

## 1. 项目概述

### 1.1 项目名称
AI Workspace GUI Agent

### 1.2 项目类型
基于 browser-use 框架的完整前后端 GUI Agent 产品

### 1.3 核心功能
三栏式 AI 工作空间：左侧会话历史栏 + 中间聊天界面 + 右侧浏览器预览面板

### 1.4 目标用户
个人用户（第一阶段无认证，后续可扩展）

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           前端 (Next.js)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  Sidebar    │  │   Chat UI   │  │   Browser   │                 │
│  │  (会话历史)  │  │  (消息流)   │  │   Preview   │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                        │
│         └────────────────┼────────────────┘                        │
│                          │                                         │
│                   ┌───────▼───────┐                                  │
│                   │  CopilotKit  │ ← AG-UI 协议                    │
│                   │  (状态同步)   │                                  │
│                   └───────┬───────┘                                  │
└───────────────────────────┼─────────────────────────────────────────┘
                            │ HTTP/SSE
                    ┌───────▼───────┐
                    │   FastAPI     │ ← 后端 API 网关
                    │   (端口 8000)  │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
        │  Agent    │ │  Session  │ │  Browser  │
        │  Service  │ │  Service  │ │  Service  │
        │ (LLM决策) │ │(SQLite存储)│ │ (CDP控制) │
        └───────────┘ └───────────┘ └───────────┘
```

### 2.2 项目组织

| 仓库 | 描述 |
|------|------|
| `browser-use` (原有) | Python 核心库 |
| `browser-use-frontend` | Next.js 前端应用 (新建) |
| `browser-use-backend` | FastAPI 后端服务 (新建) |

---

## 3. 前端规格

### 3.1 项目结构

```
frontend/                          # Next.js 应用 (独立仓库)
├── src/
│   ├── app/
│   │   ├── layout.tsx           # 根布局
│   │   ├── page.tsx             # 主页面
│   │   └── api/                 # (可选) API Routes
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx   # 聊天窗口
│   │   │   ├── MessageList.tsx  # 消息列表
│   │   │   ├── MessageItem.tsx  # 单条消息
│   │   │   ├── InputArea.tsx    # 输入区
│   │   │   └── TypingIndicator.tsx
│   │   ├── browser/
│   │   │   ├── BrowserPreview.tsx   # 浏览器预览区
│   │   │   ├── BrowserChrome.tsx    # URL 栏、控制按钮
│   │   │   └── BrowserContent.tsx   # 内容区
│   │   └── sidebar/
│   │       ├── Sidebar.tsx         # 侧边栏容器
│   │       ├── HistoryList.tsx     # 历史会话列表
│   │       └── ChatHistoryItem.tsx # 单条历史
│   ├── hooks/
│   │   ├── useChatSession.ts    # 会话管理
│   │   ├── useStreamingMessage.ts # SSE 流式消息
│   │   └── useBrowserControl.ts # 浏览器控制
│   ├── lib/
│   │   └── api.ts               # API 客户端
│   └── types/
│       └── index.ts             # 共享类型定义
├── package.json
└── next.config.js
```

### 3.2 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| 框架 | Next.js | SSR + API Routes + React 生态 |
| 状态同步 | CopilotKit | AG-UI 协议标准实现 |
| 样式 | Tailwind CSS | 快速适配 Agent 动态布局 |
| 开发语言 | TypeScript | 类型安全 |

### 3.3 组件职责

| 组件 | 职责 |
|------|------|
| ChatWindow | 聊天主容器，管理消息列表和输入区 |
| InputArea | 用户输入，支持多行文本和附件 |
| BrowserPreview | **右侧真实 Chrome 内核嵌入**，支持实时交互 |
| Sidebar | 会话历史管理 (第一阶段简化) |

### 3.4 浏览器嵌入架构

右侧浏览器面板**内嵌真实 Chrome 内核**，通过以下方式实现：

```
┌─────────────────────────────────────────────────────────────────────┐
│                         后端 (browser-use)                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │            BrowserSession (真实 Chrome 浏览器)                │  │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │  │
│  │   │ CDP Client  │  │ Page State  │  │ Input Events│         │  │
│  │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │  │
│  │          │                │                │                  │  │
│  │          └────────────────┼────────────────┘                  │  │
│  │                           │                                   │  │
│  │              ┌────────────▼────────────┐                     │  │
│  │              │   Browser Service       │                     │  │
│  │              │   (CDP WebSocket 转发)   │                     │  │
│  │              └────────────┬────────────┘                     │  │
│  └──────────────────────────┼───────────────────────────────────┘  │
│                             │ CDP WebSocket (ws://localhost:9222)  │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                         前端 (Next.js)                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              BrowserPreview 组件                             │   │
│  │   ┌────────────────────────────────────────────────────┐    │   │
│  │   │  Chrome DevTools Protocol (CDP) WebSocket Client    │    │   │
│  │   │  - 接收页面帧数据 (Page.captureScreenshot)          │    │   │
│  │   │  - 转发用户交互事件 (Input.dispatchMouseEvent)       │    │   │
│  │   └────────────────────────────────────────────────────┘    │   │
│  │                           │                                   │   │
│  │   ┌───────────────────────▼────────────────────────────┐    │   │
│  │   │  <iframe> 或 Canvas 渲染                             │    │   │
│  │   │  - 展示实时页面内容                                   │    │   │
│  │   │  - 支持点击、滚动、输入等交互                         │    │   │
│  │   └────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**实现方案**：前端通过 CDP WebSocket 直连后端的 Chrome 实例 (remote-debugging-port)

| 方式 | 说明 |
|------|------|
| 连接方式 | 前端 WebSocket 连接到 `ws://localhost:9222` (或后端代理的 ws 端点) |
| 页面获取 | 后端创建并管理 BrowserSession，前端通过 CDP 实时获取页面状态 |
| 用户交互 | 前端捕获用户点击/滚动事件，通过 CDP 转发到后端浏览器 |
| 替代方案 | 若 WebSocket 直连不可行，后端可代理 CDP 请求 |

**关键约束**：
- Chrome 必须以 `--remote-debugging-port=9222` 启动
- 前端需实现 CDP 协议的 WebSocket 客户端 (或使用已有库如 `@powerhouse-inc/cdp`)
- 浏览器状态与 Agent 控制共享同一个 BrowserSession

---

## 4. 后端规格

### 4.1 项目结构

```
backend/                          # Python FastAPI (独立仓库)
├── app/
│   ├── main.py                  # FastAPI 入口
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py              # /api/chat 端点 (SSE)
│   │   ├── sessions.py          # /api/sessions 端点
│   │   └── browser.py           # /api/browser/control 端点
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py     # Agent 核心逻辑
│   │   ├── session_service.py   # 会话管理 (SQLite)
│   │   └── browser_service.py   # 浏览器控制
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chat.py              # Pydantic 请求/响应模型
│   │   └── session.py           # 会话数据模型
│   └── db/
│       ├── __init__.py
│       └── database.py          # SQLite 连接管理
├── browser_use/                 # 核心库 (作为 dependency)
├── pyproject.toml
└── uv.lock
```

### 4.2 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| 框架 | FastAPI | 异步 + SSE 原生支持 |
| Agent 核心 | browser-use | 复用现有 CDP 控制能力 |
| 数据库 | SQLite | 零配置 + 持久化 |
| 通信协议 | SSE | 流式响应 + 简单实现 |
| 依赖管理 | uv | 遵循现有规范 |

---

## 5. API 接口设计

### 5.1 聊天接口 (SSE 流式)

**端点**: `POST /api/chat`

**请求**:
```json
{
  "session_id": "uuid7-string",
  "message": "帮我打开 Google",
  "attachments": [{ "name": "file.pdf", "type": "application/pdf" }]
}
```

**响应**: Server-Sent Events (text/event-stream)

```
event: message
data: {"content": "好的，我来帮您打开 Google", "role": "ai"}

event: action
data: {"tool": "navigate", "args": {"url": "https://google.com"}}

event: browser_state
data: {"url": "https://www.google.com", "title": "Google", "screenshot": "base64..."}

event: done
data: {}
```

### 5.2 会话管理接口

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | /api/sessions | 获取所有会话列表 |
| POST | /api/sessions | 创建新会话 |
| GET | /api/sessions/{id} | 获取会话详情 |
| PUT | /api/sessions/{id} | 更新会话 (如重命名) |
| DELETE | /api/sessions/{id} | 删除会话 |
| GET | /api/sessions/{id}/messages | 获取会话消息历史 |

### 5.3 浏览器控制接口

**端点**: `POST /api/browser/control`

**请求**:
```json
{
  "session_id": "uuid7-string",
  "action": "navigate" | "click" | "type" | "scroll" | "screenshot",
  "args": { ... }
}
```

**响应**:
```json
{
  "success": true,
  "state": { "url": "...", "title": "...", "screenshot": "..." }
}
```

---

## 6. 数据模型

### 6.1 数据库 Schema (SQLite)

```sql
-- sessions 表
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,           -- uuid7str
  title TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- messages 表
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,            -- 'user' | 'ai'
  content TEXT NOT NULL,
  attachments TEXT,              -- JSON array
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- browser_state 表
CREATE TABLE browser_states (
  session_id TEXT PRIMARY KEY,
  url TEXT,
  title TEXT,
  screenshot TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### 6.2 Pydantic 模型

```python
# chat.py
class ChatRequest(BaseModel):
    session_id: str
    message: str
    attachments: list[Attachment] = []

class Attachment(BaseModel):
    name: str
    type: str
    data: str | None = None

# session.py
class Session(BaseModel):
    id: str = Field(default_factory=uuid7str)
    title: str
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    id: str = Field(default_factory=uuid7str)
    session_id: str
    role: Literal["user", "ai"]
    content: str
    attachments: list[Attachment] = []
    created_at: datetime
```

---

## 7. SSE 事件类型

```typescript
// 前端 types/index.ts
type SSEEvent =
  | { type: "message"; content: string; role: "ai" | "user" }
  | { type: "action"; tool: string; args: Record<string, any> }
  | { type: "browser_state"; url: string; title: string; screenshot?: string }
  | { type: "thinking"; content: string }
  | { type: "done" }
  | { type: "error"; message: string }
```

---

## 8. 第一阶段交付目标 (MVP)

### 后端
- [ ] FastAPI 启动 (uvicorn, 端口 8000)
- [ ] `/api/chat` SSE 端点 (调用 Agent)
- [ ] `/api/sessions` CRUD
- [ ] SQLite 会话持久化
- [ ] 浏览器状态存储

### 前端
- [ ] Next.js 项目初始化
- [ ] ChatWindow + InputArea
- [ ] SSE 流式消息接收
- [ ] BrowserPreview **(真实 Chrome CDP 嵌入)**
- [ ] Agent 状态指示器
- [ ] 确认对话框 (HITL)
- [ ] 基础错误处理

### 集成
- [ ] 前后端通过 `/api/chat` 通信
- [ ] 流式响应展示 (typing indicator)
- [ ] 浏览器状态同步

---

## 9. 约束条件

| 约束 | 说明 |
|------|------|
| ID 生成 | 使用 `uuid7str` |
| 超时设置 | 所有外部服务调用必须设置超时 |
| 错误处理 | 所有外部调用必须 try-catch |
| 依赖管理 | 后端使用 `uv`，前端使用 `pnpm` |
| 认证 | 第一阶段无认证，单实例 |
| 浏览器嵌入 | Chrome 必须以 `--remote-debugging-port=9222` 启动 |
| CDP 协议 | 前端需实现 CDP WebSocket 客户端 |
| Human-in-the-Loop | Agent 支持 pause/resume/stop，敏感操作需确认 |

---

## 10. 参考原型

### 10.1 前端参考原型
原型文件: `.harness/wiki/frontend-design/ai-workspace-three-column-3.html`

核心特性:
- 三栏布局 (sidebar + chat + browser)
- 聊天消息展示 (Markdown 支持)
- 输入区域 (支持附件)
- 浏览器预览区 (Chrome 风格)
- 侧边栏折叠功能

### 10.2 后端 Agent 参考
参考文件: `examples/interrupt.py`

核心实现要点:
- Agent 核心逻辑使用 `browser_use.Agent`
- 支持 `on_step_start` 和 `on_step_end` hooks
- 通过 `agent.pause()` / `agent.resume()` 实现中断
- 支持 `/pause`, `/resume`, `/stop` 命令

### 10.3 Human-in-the-Loop 设计

GUI Agent 需要支持人工干预决策流程：

**中断触发场景**:
| 场景 | 触发条件 | 等待行为 |
|------|----------|----------|
| 敏感操作 | 点击危险按钮、提交表单 | 等待确认 |
| 决策分支 | AI 无法确定下一步 | 显示选项供选择 |
| 异常处理 | 页面未按预期加载 | 提供重试/跳过选项 |
| 认证拦截 | 需要登录/验证码 | 暂停等待人工处理 |

**交互模式**:
```
Agent 执行中...
    ↓ (触发中断条件)
前端显示确认对话框 (Agent 暂停)
    ↓ (用户选择)
Resume: 继续执行 / Skip: 跳过 / Stop: 终止任务
    ↓
Agent 继续或终止
```

**API 扩展**:
```python
# 后端新增端点
POST /api/agent/pause     # 暂停 Agent
POST /api/agent/resume    # 继续执行
POST /api/agent/stop       # 停止 Agent
GET  /api/agent/status     # 获取 Agent 状态 (running/paused/stopped)

# SSE 新增事件
event: waiting_confirmation
data: {"type": "confirm", "message": "确认执行此操作?", "options": ["confirm", "skip", "stop"]}

event: paused
data: {"reason": "awaiting_confirmation"}
```

**前端组件**:
- `ConfirmDialog` - 确认对话框组件
- `AgentStatusIndicator` - 显示 Agent 状态 (running/paused)
- `InterruptOptions` - 中断选项按钮组