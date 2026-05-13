# 任务拆分清单: AG-UI 协议集成

## Task 1: 后端 AG-UI HTTP Agent 端点实现

| 字段 | 内容 |
|------|------|
| 目标 | 在 FastAPI 后端实现符合 AG-UI 协议的 HTTP Agent 端点 |
| 范围 | 新建 `backend/app/api/agui.py`，实现 `/agui` 端点 |
| 输入 | `RunAgentInput` JSON (threadId, messages, context, state, tools, forwardedProps) |
| 输出 | SSE 流输出 `BaseEvent` 事件 |
| 验收标准 | 1. 端点响应 200 OK 2. 支持 RUN_STARTED/RUN_FINISHED/RUN_ERROR 3. 支持 TEXT_MESSAGE_* 事件 4. 支持 TOOL_CALL_* 事件 5. 支持 STATE_SNAPSHOT 事件 |
| 依赖 | Task 2 (Agent Service 改造) |
| 优先级 | P0 |

### 子任务

- [x] 创建 `backend/app/api/agui.py`
- [x] 实现 `RunAgentInput` Pydantic 模型
- [x] 实现 `BaseEvent` 事件类序列化
- [x] 实现 `/agui` POST 端点
- [x] 集成 `AgentService` 的 `run_agent` 方法
- [x] 添加 SSE 流式响应生成器
- [x] 错误处理和异常事件发送

---

## Task 2: Agent Service 改造 - AG-UI 事件映射

| 字段 | 内容 |
|------|------|
| 目标 | 改造 `AgentService` 以支持 AG-UI 标准事件格式 |
| 范围 | 修改 `backend/app/services/agent_service.py` |
| 输入 | `message`, `session_id`, `on_event` 回调 |
| 输出 | AG-UI 格式的 `BaseEvent` 字典 |
| 验收标准 | 1. `step_start` → `STEP_STARTED` 2. `step_end` → `STEP_FINISHED` 3. `message` → `TEXT_MESSAGE_*` 4. `browser_state` → `STATE_SNAPSHOT` 5. 保持 pause/resume/stop 逻辑 6. 支持 `INTERRUPT` / `RESUME` 事件 (HITL) |
| 依赖 | 无 |
| 优先级 | P0 |

### 子任务

- [x] 分析现有事件到 AG-UI 事件的映射关系
- [x] 实现事件类型常量定义
- [x] 改造 `on_step_start` 发送 `STEP_STARTED`
- [x] 改造 `on_step_end` 发送 `STEP_FINISHED` + `TEXT_MESSAGE_*`
- [x] 改造 browser_state 为 `STATE_SNAPSHOT`
- [x] 实现 `INTERRUPT` 事件（暂停时触发）
- [x] 实现 `RESUME` 事件（恢复时触发）
- [x] 添加 `RUN_STARTED` / `RUN_FINISHED` / `RUN_ERROR`
- [x] 完整 State Sync 支持

---

## Task 3: 前端 CopilotKit API Route 实现

| 字段 | 内容 |
|------|------|
| 目标 | 创建 Next.js CopilotKit API Route Handler |
| 范围 | 新建 `frontend/src/app/api/copilotkit/route.ts` |
| 输入 | NextRequest (CopilotKit 格式) |
| 输出 | CopilotKit 运行时响应 |
| 验收标准 | 1. 路由响应 200 OK 2. 使用 `copilotRuntimeNextJSAppRouterEndpoint` 3. 注册 `HttpAgent` 指向后端 `/agui` 4. 支持多 Agent 配置 |
| 依赖 | Task 1 (后端端点) |
| 优先级 | P0 |

### 子任务

- [x] 创建 `frontend/src/app/api/copilotkit/` 目录
- [x] 创建 `route.ts`
- [x] 导入 `CopilotRuntime`, `HttpAgent`, `copilotRuntimeNextJSAppRouterEndpoint`
- [x] 配置 `AGENT_URL` 环境变量
- [x] 注册默认 `HttpAgent`
- [x] 实现 POST handler
- [x] 错误处理

---

## Task 4: 前端 CopilotKitProvider 集成

| 字段 | 内容 |
|------|------|
| 目标 | 在 Next.js App 中集成 CopilotKitProvider |
| 范围 | 创建 `CopilotKitProvider.tsx`，提供集成说明 |
| 输入 | `CopilotKitProvider` props |
| 输出 | 全局 Provider 配置 + 集成说明文档 |
| 验收标准 | 1. Provider 组件创建完成 2. 提供 layout.tsx 集成说明 3. 配置 `runtimeUrl` 指向 `/api/copilotkit` |
| 依赖 | Task 3 |
| 优先级 | P0 |
| 状态 | 部分完成 (layout.tsx 待创建) |

### 子任务

- [x] 安装 `@copilotkit/react-core` 依赖 (已添加到 package.json)
- [x] 导入 `CopilotKitProvider`
- [x] 创建 `CopilotKitProvider.tsx` 组件
- [x] 配置 runtimeUrl
- [ ] 验证无重复 Provider 警告 (待集成到 layout)

---

## Task 5: ChatWindow 组件重构

| 字段 | 内容 |
|------|------|
| 目标 | 重构 `ChatWindow` 使用 `useAgent` hook |
| 范围 | 修改 `frontend/src/components/chat/ChatWindow.tsx` |
| 输入 | `useAgent()` 返回的 messages, sendMessage, isLoading |
| 输出 | React 组件 |
| 验收标准 | 1. 使用 `useAgent` 替代 `streamChat` 2. 消息通过 CopilotKit 管理 3. 保持现有的 UI 展示 4. 保持 `onEvent` 回调给父组件 |
| 依赖 | Task 4 |
| 优先级 | P0 |

### 子任务

- [x] 导入 `useAgent` from `@copilotkit/react-core`
- [x] 删除 `streamChat` 和 `getMessages` 调用
- [x] 使用 `const { messages, sendMessage, isLoading } = useAgent()`
- [x] 改造 `handleSend` 调用 `sendMessage(text)`
- [x] 使用 CopilotKit 管理的 messages 状态
- [x] 保持 `onEvent` 回调兼容
- [x] 处理 `isLoading` 状态

---

## Task 6: 单元测试编写

| 字段 | 内容 |
|------|------|
| 目标 | 为 AG-UI 集成编写单元测试 |
| 范围 | `backend/tests/test_agui.py`, `frontend/tests/` |
| 输入 | 模拟 RunAgentInput, SSE 事件流 |
| 输出 | 测试用例覆盖 |
| 验收标准 | 1. 后端端点测试 2. 事件序列化测试 3. 前端组件测试 4. 覆盖率 > 80% |
| 依赖 | Task 1-5 |
| 优先级 | P1 |

### 子任务

- [ ] 创建 `backend/tests/test_agui.py`
- [ ] 测试 RunAgentInput 模型验证
- [ ] 测试 BaseEvent 序列化
- [ ] 测试 `/agui` 端点
- [ ] 测试事件流生成
- [ ] 创建前端测试 (Vitest/Jest)

---

## Task 7: 废弃旧端点清理

| 字段 | 内容 |
|------|------|
| 目标 | 直接废弃 `/chat` 端点，清理相关代码 |
| 范围 | 删除 `backend/app/api/chat.py` 及相关引用 |
| 输入 | 现有 `/chat` 端点代码 |
| 输出 | 清理后的代码库 |
| 验收标准 | 1. `/chat` 端点已删除 2. 无残留引用 3. 前端不再依赖旧端点 |
| 依赖 | Task 1-5 |
| 优先级 | P2 |

### 子任务

- [ ] 删除 `backend/app/api/chat.py`
- [ ] 从后端路由注册中移除 chat 路由
- [ ] 删除前端 `lib/api.ts` 中的 `streamChat` 和 `getMessages`
- [ ] 验证无残留引用

---

## 任务依赖关系图

```
Task 1 (后端AGUI端点)
    ↑
Task 2 (AgentService改造) ← 无依赖
    ↑
Task 3 (前端API Route) → Task 4 (CopilotKitProvider)
    ↑                       ↑
    |_______________________|
            Task 5 (ChatWindow重构)
                    ↑
                    Task 6 (单元测试)
                    ↑
                    Task 7 (向后兼容)
```

---

## 优先级排序

1. **P0 (阻塞)**: Task 1, 2, 3, 4, 5
2. **P1 (重要)**: Task 6
3. **P2 (可选)**: Task 7
