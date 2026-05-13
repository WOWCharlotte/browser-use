# 需求规格说明书: AG-UI 协议集成

## 1. 概述

### 1.1 背景
browser-use 项目当前使用自定义 SSE 格式进行前后端通信，不符合 AG-UI (Agent User Interaction) 开放协议标准。需要集成 CopilotKit + AG-UI 协议，实现：
- 前后端通信标准化
- 与主流 Agent 前端框架的互操作性
- 支持 Human-in-the-Loop 中断机制

### 1.2 目标
将前后端通信从自定义 SSE 格式迁移至 AG-UI 协议标准，使用 CopilotKit 作为前端集成层。

## 2. 输入

### 2.1 后端 API

| 参数 | 类型 | 来源 | 描述 | 校验规则 |
|------|------|------|------|----------|
| session_id | string | 前端 | 会话唯一标识 | 必填，非空，UUID 格式 |
| message | string | 前端 | 用户消息 | 必填，最大 10000 字符 |
| attachments | array | 前端 | 附件列表 | 可选，默认空数组 |

### 2.2 RunAgentInput (AG-UI 标准格式)

| 参数 | 类型 | 来源 | 描述 |
|------|------|------|------|
| threadId | string | 前端/系统 | 线程 ID |
| runId | string | 系统 | 运行时唯一 ID |
| messages | Message[] | 前端 | 消息历史 |
| tools | Tool[] | 后端注册 | 可用工具列表 |
| context | ContextEntry[] | 前端 | 上下文变量 |
| state | State | 后端 | Agent 状态快照 |
| forwardedProps | object | 前端 | 透传属性 |

## 3. 输出

### 3.1 后端响应 (SSE 流)

| 事件类型 | 描述 | 数据结构 |
|----------|------|----------|
| RUN_STARTED | 运行开始 | `{ type: "RUN_STARTED", runId: string }` |
| TEXT_MESSAGE_START | 文本消息开始 | `{ type: "TEXT_MESSAGE_START", messageId: string, role: "user" \| "assistant" }` |
| TEXT_MESSAGE_CONTENT | 文本内容块 | `{ type: "TEXT_MESSAGE_CONTENT", content: string }` |
| TEXT_MESSAGE_END | 文本消息结束 | `{ type: "TEXT_MESSAGE_END", messageId: string }` |
| TOOL_CALL_START | 工具调用开始 | `{ type: "TOOL_CALL_START", toolCallId: string, toolName: string }` |
| TOOL_CALL_ARGS | 工具参数 | `{ type: "TOOL_CALL_ARGS", toolCallId: string, args: object }` |
| TOOL_CALL_RESULT | 工具结果 | `{ type: "TOOL_CALL_RESULT", toolCallId: string, result: string }` |
| TOOL_CALL_END | 工具调用结束 | `{ type: "TOOL_CALL_END", toolCallId: string }` |
| STEP_STARTED | 步骤开始 | `{ type: "STEP_STARTED", stepNumber: number }` |
| STEP_FINISHED | 步骤结束 | `{ type: "STEP_FINISHED", stepNumber: number }` |
| STATE_SNAPSHOT | 状态快照 | `{ type: "STATE_SNAPSHOT", state: object }` |
| RUN_FINISHED | 运行结束 | `{ type: "RUN_FINISHED", outcome: "success" \| "stopped" }` |
| RUN_ERROR | 运行错误 | `{ type: "RUN_ERROR", error: string }` |

### 3.2 前端 API

| 返回值 | 类型 | 格式 | 描述 |
|--------|------|------|------|
| messages | Message[] | JSON Array | 会话消息列表 |
| stream | Observable | RxJS | SSE 事件流 |

## 4. 功能列表

### 4.1 后端功能

- [ ] 实现 `/api/copilotkit` POST 端点，接收 RunAgentInput
- [ ] 实现 AG-UI BaseEvent SSE 流式输出
- [ ] 支持 `RUN_STARTED` / `RUN_FINISHED` / `RUN_ERROR` 生命周期事件
- [ ] 支持 `TEXT_MESSAGE_*` 文本消息事件
- [ ] 支持 `TOOL_CALL_*` 工具调用事件
- [ ] 支持 `STEP_STARTED` / `STEP_FINISHED` 步骤事件
- [ ] 支持 `STATE_SNAPSHOT` 状态同步事件
- [ ] 保持现有的 pause/resume/stop 机制
- [ ] 保持现有的 browser_state 事件

### 4.2 前端功能

- [ ] 创建 `/api/copilotkit` Next.js Route Handler
- [ ] 集成 `@copilotkit/runtime` 的 `CopilotRuntime`
- [ ] 集成 `@copilotkit/react-core` 的 `CopilotKitProvider`
- [ ] 使用 `useAgent` hook 替代自定义 `streamChat`
- [ ] 重构 `ChatWindow` 组件使用 CopilotKit 事件
- [ ] 保持现有的 UI 组件 (MessageList, InputArea, MessageItem)

### 4.3 向后兼容

- [ ] 现有会话数据迁移策略
- [ ] API 端点版本管理

## 5. 边界条件

| 条件 | 描述 |
|------|------|
| 空消息 | 返回错误，不创建 agent |
| 超长消息 | 截断至 10000 字符 |
| 并发会话 | 每个 session_id 独立 agent 实例 |
| Agent 运行超时 | 30 秒无响应发送 heartbeat |
| 浏览器未初始化 | 自动创建新浏览器会话 |
| 消息流中断 | 支持断点重连 |

## 6. 异常处理

| 异常 | 处理方式 |
|------|----------|
| LLM API 超时 | 返回 `RUN_ERROR`，错误信息包含 timeout |
| 浏览器连接失败 | 返回 `RUN_ERROR`，错误信息包含 connection failed |
| 无效 session_id | 返回 400 Bad Request |
| Agent 内部错误 | 捕获异常，发送 `RUN_ERROR` 事件 |
| SSE 连接断开 | 前端自动重连机制 |

## 7. 技术约束

### 7.1 依赖版本

| 库 | 版本 | 用途 |
|----|------|------|
| @copilotkit/runtime | ^1.0.0 | CopilotKit 运行时 |
| @copilotkit/react-core | ^1.0.0 | React Hooks |
| @ag-ui/client | ^0.20.0 | AG-UI TypeScript 客户端 |
| browser-use | (当前) | 核心 Agent |

### 7.2 兼容性

- 前端: Next.js 14+ (App Router)
- 后端: Python 3.11+, FastAPI
- 协议: AG-UI 0.0.47+
