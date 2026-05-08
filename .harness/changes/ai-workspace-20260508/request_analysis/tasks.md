# AI Workspace GUI Agent - 任务拆解

## 任务概述

本项目分为两个独立仓库：前端 (browser-use-frontend) 和后端 (browser-use-backend)。以下任务按仓库分组。

---

## 第一部分：后端开发 (browser-use-backend)

### 任务 1: 项目初始化
**目标**: 创建 FastAPI 项目结构
**验收标准**:
- [ ] pyproject.toml 正确配置，包含 fastapi, uvicorn, browser-use, aiosqlite
- [ ] 项目目录结构符合 `.harness/rules/工程结构.md` 规范
- [ ] `uv sync` 成功执行

**子任务**:
1. 创建 `backend/app/` 目录结构
2. 创建 `pyproject.toml` (依赖: fastapi, uvicorn[standard], browser-use, aiosqlite, pydantic)
3. 配置 `uv.lock`
4. 创建 `app/main.py` 入口文件

---

### 任务 2: 数据库层实现
**目标**: 实现 SQLite 会话持久化
**验收标准**:
- [ ] SQLite 数据库初始化成功
- [ ] sessions, messages, browser_states 表创建
- [ ] CRUD 操作通过 Pydantic 模型验证

**子任务**:
1. 创建 `app/db/database.py` - SQLite 连接管理
2. 创建 `app/models/session.py` - Session Pydantic 模型
3. 创建 `app/models/chat.py` - Chat Pydantic 模型
4. 实现 `app/services/session_service.py` - 会话 CRUD

---

### 任务 3: 会话管理 API
**目标**: 实现 `/api/sessions` REST 接口
**验收标准**:
- [ ] GET /api/sessions 返回会话列表
- [ ] POST /api/sessions 创建新会话
- [ ] GET /api/sessions/{id} 返回会话详情
- [ ] PUT /api/sessions/{id} 更新会话
- [ ] DELETE /api/sessions/{id} 删除会话
- [ ] GET /api/sessions/{id}/messages 返回消息历史

**子任务**:
1. 创建 `app/api/sessions.py`
2. 实现 `SessionService` 的 API 端点
3. 添加请求验证和错误处理

---

### 任务 4: Agent 服务集成
**目标**: 集成 browser-use Agent 核心
**验收标准**:
- [ ] AgentService 正确调用 browser-use
- [ ] 支持流式响应 (SSE)
- [ ] 正确处理 Agent 决策循环

**子任务**:
1. 创建 `app/services/agent_service.py`
2. 实现 `AgentService.process_message()` 方法
3. 集成 browser-use 的 Agent 类
4. 配置 LLM (从环境变量读取)

---

### 任务 5: 聊天 API (SSE)
**目标**: 实现 `/api/chat` 流式聊天端点
**验收标准**:
- [ ] POST /api/chat 返回 SSE 流
- [ ] 每条 AI 响应通过 SSE 发送
- [ ] 支持浏览器动作事件 (navigate, click, etc.)
- [ ] 支持 typing indicator

**子任务**:
1. 创建 `app/api/chat.py`
2. 实现 SSE 流式响应逻辑
3. 处理浏览器状态更新事件
4. 实现错误处理和连接断开

---

### 任务 6: 浏览器控制 API (CDP 集成)
**目标**: 通过 CDP 控制真实 Chrome 浏览器
**验收标准**:
- [ ] Chrome 以 remote-debugging-port 模式启动
- [ ] BrowserSession 管理浏览器生命周期
- [ ] CDP WebSocket 端点暴露给前端
- [ ] 支持 navigate, click, type, scroll, screenshot 等 CDP 命令

**子任务**:
1. 创建 `app/services/browser_service.py`
2. 实现 Chrome 启动和 CDP 连接
3. 创建 `/ws/browser` WebSocket 端点 (供前端 CDP 直连)
4. 或实现 CDP 请求代理接口
5. 存储浏览器状态到 SQLite

---

## 第二部分：前端开发 (browser-use-frontend)

### 任务 7: 项目初始化
**目标**: 创建 Next.js 项目
**验收标准**:
- [ ] Next.js 14+ 项目创建成功
- [ ] TypeScript 配置正确
- [ ] Tailwind CSS 集成
- [ ] CopilotKit 集成

**子任务**:
1. `npx create-next-app@latest frontend`
2. 配置 `tailwind.config.ts`
3. 安装 CopilotKit: `pnpm add @copilotkit/react`
4. 创建基础目录结构

---

### 任务 8: 类型定义
**目标**: 定义前后端共享类型
**验收标准**:
- [ ] SSE 事件类型定义完整
- [ ] API 请求/响应类型与后端一致
- [ ] 可被前后端共用

**子任务**:
1. 创建 `src/types/index.ts`
2. 定义 `SSEEvent` 联合类型
3. 定义 `ChatRequest`, `Session`, `Message` 类型
4. 导出类型供其他模块使用

---

### 任务 9: API 客户端
**目标**: 实现与后端通信的客户端
**验收标准**:
- [ ] `api.ts` 封装所有 REST 调用
- [ ] SSE 流式消息接收正确
- [ ] 请求/响应类型安全

**子任务**:
1. 创建 `src/lib/api.ts`
2. 实现 `fetchSessions()`, `createSession()` 等
3. 实现 `streamChat()` - SSE 流式接收
4. 实现 `controlBrowser()` - 浏览器控制

---

### 任务 10: ChatWindow 组件
**目标**: 实现聊天主界面
**验收标准**:
- [ ] 消息列表正确显示
- [ ] Markdown 渲染支持
- [ ] 打字指示器动画
- [ ] 消息附件展示

**子任务**:
1. 创建 `src/components/chat/MessageItem.tsx`
2. 创建 `src/components/chat/MessageList.tsx`
3. 创建 `src/components/chat/TypingIndicator.tsx`
4. 创建 `src/components/chat/ChatWindow.tsx`

---

### 任务 11: InputArea 组件
**目标**: 实现用户输入区域
**验收标准**:
- [ ] 多行文本输入支持
- [ ] Enter 发送, Shift+Enter 换行
- [ ] 附件上传按钮
- [ ] 附件预览芯片

**子任务**:
1. 创建 `src/components/chat/InputArea.tsx`
2. 实现 `textarea` 自动增长
3. 实现附件选择和预览
4. 实现发送逻辑和状态管理

---

### 任务 12: BrowserPreview 组件 (真实 Chrome 内核)
**目标**: 实现嵌入真实 Chrome 的浏览器预览
**验收标准**:
- [ ] 通过 CDP WebSocket 连接后端 Chrome
- [ ] 实时接收页面截图/帧数据
- [ ] 用户可在预览区进行点击、滚动、输入等交互
- [ ] URL 栏显示当前页面
- [ ] 前进/后退/刷新按钮

**子任务**:
1. 安装 CDP 客户端库 (如 `@powerhouse-inc/cdp` 或 `chrome-remote-interface`)
2. 创建 `src/components/browser/BrowserChrome.tsx`
3. 创建 `src/components/browser/BrowserContent.tsx` - Canvas/iframe 渲染
4. 创建 `src/components/browser/BrowserPreview.tsx`
5. 实现 CDP WebSocket 客户端
6. 实现交互事件转发 (click, scroll, input)
7. 实现 traffic lights (红绿灯按钮)

---

### 任务 13: Sidebar 组件 (简化版)
**目标**: 实现简化版侧边栏
**验收标准**:
- [ ] 会话列表展示
- [ ] 新建聊天按钮
- [ ] 基本折叠功能

**子任务**:
1. 创建 `src/components/sidebar/ChatHistoryItem.tsx`
2. 创建 `src/components/sidebar/HistoryList.tsx`
3. 创建 `src/components/sidebar/Sidebar.tsx`
4. 实现会话切换逻辑

---

### 任务 14: 主页面集成
**目标**: 实现三栏布局主页面
**验收标准**:
- [ ] 三栏布局正确显示
- [ ] 响应式适配
- [ ] 侧边栏折叠/展开

**子任务**:
1. 创建 `src/app/page.tsx`
2. 实现三栏 grid 布局
3. 实现 hooks: `useChatSession`, `useStreamingMessage`
4. 连接所有组件到 API

---

## 第三部分：集成与部署

### 任务 15: 前后端集成 (CDP WebSocket)
**目标**: 验证前后端通信及真实浏览器集成
**验收标准**:
- [ ] 前端通过 WebSocket 连接到 CDP
- [ ] 聊天消息能正确发送到后端
- [ ] SSE 流式响应正确接收
- [ ] 浏览器状态能实时更新到前端
- [ ] 用户交互能正确转发到浏览器

**子任务**:
1. 配置 CORS (后端)
2. 配置 WebSocket 代理 (前端 dev server)
3. 实现 CDP WebSocket 通道
4. 端到端测试聊天 + 浏览器交互流程

---

### 任务 16: 部署配置
**目标**: 准备部署文档
**验收标准**:
- [ ] 后端可通过 `uv run uvicorn app.main:app` 启动
- [ ] 前端可通过 `pnpm dev` 启动
- [ ] 部署文档清晰

**子任务**:
1. 编写 README.md (部署说明)
2. 配置环境变量模板
3. 验证 Docker 可行性 (可选)

---

## 第四部分：Human-in-the-Loop (HITL)

### 任务 17: Agent 中断机制
**目标**: 实现 Agent 暂停/恢复/停止控制
**验收标准**:
- [ ] `agent.pause()` 暂停 Agent 执行
- [ ] `agent.resume()` 恢复 Agent 执行
- [ ] `agent.stop()` 停止 Agent
- [ ] Agent 状态可通过 API 查询

**子任务**:
1. 创建 `app/api/agent.py`
2. 实现 `/api/agent/pause`, `/api/agent/resume`, `/api/agent/stop`, `/api/agent/status`
3. 在 AgentService 中管理 Agent 生命周期
4. 参考 `examples/interrupt.py` 实现 hooks

---

### 任务 18: SSE 中断事件
**目标**: 前端接收中断事件并显示确认对话框
**验收标准**:
- [ ] SSE 发送 `waiting_confirmation` 事件
- [ ] SSE 发送 `paused` 事件
- [ ] 前端显示确认对话框
- [ ] 用户选择能正确发送到后端

**子任务**:
1. 更新 SSE 事件类型定义
2. 实现 `waiting_confirmation` 事件发送
3. 创建 `ConfirmDialog` 组件
4. 创建 `AgentStatusIndicator` 组件

---

### 任务 19: 确认对话框组件
**目标**: 实现前端确认对话框
**验收标准**:
- [ ] 显示操作描述
- [ ] 提供 Confirm/Skip/Stop 选项
- [ ] 选择结果通过 API 发送
- [ ] 动画过渡效果

**子任务**:
1. 创建 `src/components/agent/ConfirmDialog.tsx`
2. 创建 `src/components/agent/AgentStatusIndicator.tsx`
3. 实现中断选项按钮组
4. 实现对话框动画

---

## 依赖关系图 (完整版)

```
后端:
task1(项目初始化)
    ↓
task2(数据库层) ← task1
    ↓
task3(会话管理API) ← task2
    ↓
task4(Agent集成) ← task3
    ↓
task5(聊天API) ← task4
    ↓
task6(浏览器控制API) ← task5
    ↓
task17(Agent中断机制) ← task5

前端:
task7(项目初始化)
    ↓
task8(类型定义)
    ↓
task9(API客户端) ← task8
    ↓
task10(ChatWindow) ← task8, task9
    ↓
task11(InputArea) ← task9
    ↓
task12(BrowserPreview) ← task9
    ↓
task13(Sidebar)
    ↓
task14(主页面集成) ← task10, task11, task12, task13
    ↓
task18(SSE中断事件) ← task14
    ↓
task19(确认对话框) ← task18

集成:
task15(集成) ← task6, task14
    ↓
task16(部署)
```

---

## 验收标准汇总

| 任务 | 验收条件 |
|------|----------|
| 1 | uv sync 成功 |
| 2 | 数据库表创建成功，CRUD 工作 |
| 3 | 所有 session API 返回正确 |
| 4 | Agent 能处理消息并返回决策 |
| 5 | SSE 流正确发送 events |
| 6 | 浏览器动作执行成功 |
| 7 | Next.js dev server 启动 |
| 8 | TypeScript 编译无错误 |
| 9 | API 调用正常工作 |
| 10-13 | 组件正确渲染和交互 |
| 14 | 三栏布局完整可用 |
| 15 | 端到端聊天流程工作 |
| 16 | 可部署并运行 |