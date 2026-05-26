# Chat 组件

## 组件概述

Chat 组件模块提供 AI 对话界面，基于 CopilotKit v2 的官方预构建组件实现。通过 AG-UI (Agent-User Interaction) 协议与后端 Agent 通信，支持文本对话和文件附件上传。

## 主要子组件

| 组件 | 文件 | 说明 |
|------|------|------|
| ChatWindow | `ChatWindow.tsx` | AI 对话窗口主组件 |

## 子组件功能说明

### ChatWindow

**功能**: 封装 CopilotKit 的 `CopilotChat` 组件，提供完整的 AI 对话体验，包括消息历史加载、实时对话和文件附件支持。

**Props**:
- `sessionId?: string` — 当前会话 ID，用于加载历史消息和关联对话
- `onMessageSent?: () => void` — 新消息发送后的回调（用于通知侧边栏刷新）

**核心行为**:

1. **AG-UI 协议通信**: 使用 `useAgent({ agentId: "default" })` 连接后端 AG-UI 端点
2. **历史消息加载**: 当 `sessionId` 变化时，从后端加载历史消息并注入到 CopilotKit agent
3. **消息变更检测**: 通过 `agent.subscribe()` 订阅消息变更，检测新消息并触发 `onMessageSent` 回调
4. **文件附件**: 支持 `.xlsx`, `.xls`, `.md`, `.markdown` 格式，最大 5MB
5. **自适应高度**: 监听窗口 resize 事件，动态调整聊天窗口高度

**CopilotKit 配置**:
```typescript
<CopilotChat
  agentId="default"        // AG-UI agent 标识
  threadId={sessionId}     // 会话线程 ID
  attachments={{
    enabled: true,
    accept: ".xlsx,.xls,.md,.markdown",
    maxSize: 5 * 1024 * 1024,  // 5MB
  }}
/>
```

## 与后端的交互逻辑

### 通信协议

ChatWindow 通过两种方式与后端交互：

1. **AG-UI 协议（主要）**: CopilotKit 自动处理与后端 AG-UI 端点的通信，包括消息发送、流式响应、工具调用等
2. **REST API（辅助）**: 用于加载历史消息

### 相关 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/sessions/{sessionId}/messages` | GET | 获取会话历史消息 |
| AG-UI 端点（由 CopilotKit 管理） | POST | 发送消息、接收 AI 响应 |

### AG-UI 通信流程

```
用户输入消息
    ↓
CopilotChat 组件 → CopilotKit HttpAgent → 后端 AG-UI 端点
    ↓
后端 Agent 处理（可能触发浏览器操作、测试执行等）
    ↓
AG-UI 流式响应 → CopilotChat 渲染 AI 回复
    ↓
agent.subscribe() 检测新消息 → onMessageSent() 通知父组件
```

### 历史消息加载流程

```
sessionId 变化
    ↓
调用 getMessages(sessionId) — GET /api/sessions/{id}/messages
    ↓
将消息转换为 CopilotKit 格式 { id, role, content }
    ↓
agent.setMessages(copilotMsgs) 注入历史
```

### 数据类型

```typescript
interface Message {
  id: string;
  session_id: string;
  role: "user" | "ai";
  content: string;
  attachments: Attachment[];
  created_at: string;
}

interface Attachment {
  name: string;
  type: string;
  data?: string;
}
```
