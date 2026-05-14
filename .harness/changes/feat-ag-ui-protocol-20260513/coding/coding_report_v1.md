# 编码报告: feat-ag-ui-protocol-20260513

## 编码阶段总结

### 完成时间
2026-05-13

### 实现的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/api/agui.py` | 新建 | AG-UI HTTP Agent 端点实现 |
| `backend/app/services/agent_service.py` | 修改 | AG-UI 事件映射改造 |
| `frontend/src/app/api/copilotkit/route.ts` | 新建 | CopilotKit API Route Handler |
| `frontend/src/components/CopilotKitProvider.tsx` | 新建 | CopilotKitProvider 组件 |
| `frontend/src/components/chat/ChatWindow.tsx` | 修改 | 重构为使用 useAgent |
| `frontend/package.json` | 修改 | 添加 CopilotKit 依赖 |

---

## Task 1: 后端 AG-UI HTTP Agent 端点

### backend/app/api/agui.py

**实现内容**:
- `RunAgentInput` Pydantic 模型 (threadId, runId, messages, tools, context, state, forwardedProps)
- `BaseEvent` 及子类 (RunStartedEvent, RunFinishedEvent, TextMessageStartEvent, 等)
- `/agui` POST 端点
- SSE 流式响应生成器
- 错误处理和异常事件发送

**关键代码片段**:

```python
@router.post("/agui")
async def agui_endpoint(input_data: RunAgentInput) -> StreamingResponse:
    """AG-UI Protocol HTTP Agent Endpoint"""
    run_id = input_data.run_id or str(uuid.uuid4())
    # ... 事件生成器实现
```

---

## Task 2: Agent Service 改造

### backend/app/services/agent_service.py

**实现内容**:
- AG-UI 事件类型常量定义
- 事件映射改造:
  - `step_start` → `STEP_STARTED`
  - `step_end` → `STEP_FINISHED` + `TEXT_MESSAGE_*`
  - `browser_state` → `STATE_SNAPSHOT`
- HITL 中断事件 (`INTERRUPT` / `RESUME`)
- 生命周期事件 (`RUN_STARTED` / `RUN_FINISHED` / `RUN_ERROR`)

**事件映射表**:

| 原事件 | AG-UI 事件 |
|--------|-----------|
| step_start | STEP_STARTED |
| step_end | STEP_FINISHED + TEXT_MESSAGE_* |
| browser_state | STATE_SNAPSHOT |
| 暂停 | INTERRUPT |
| 恢复 | RESUME |

---

## Task 3: 前端 CopilotKit API Route

### frontend/src/app/api/copilotkit/route.ts

**实现内容**:
- `CopilotRuntime` 配置
- `HttpAgent` 创建，指向后端 `/agui`
- 多 Agent 配置支持
- POST handler 实现

**关键代码片段**:

```typescript
const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8888/api/agui";

const agents: Record<string, AbstractAgent> = {
    default: createAgent(),
    agentic_chat: createAgent(),
    // ...
};

export const POST = async (req: NextRequest) => {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
        runtime: new CopilotRuntime({ agents }),
    });
    return await handleRequest(req);
};
```

---

## Task 4: CopilotKitProvider 集成

### frontend/src/components/CopilotKitProvider.tsx

**实现内容**:
- `CopilotKit` 组件包装
- `runtimeUrl` 配置
- `agent` 属性配置

**集成说明**: 见 `frontend_integration_note.md`

---

## Task 5: ChatWindow 重构

### frontend/src/components/chat/ChatWindow.tsx

**实现内容**:
- 替换 `streamChat` 为 `useAgent` hook
- 消息状态同步
- `sendMessage` 集成
- `onEvent` 回调保持兼容

**关键代码片段**:

```typescript
const { messages: agentMessages, sendMessage, isLoading } = useAgent({
    agent: "default",
});

const handleSend = async (text: string) => {
    await sendMessage(text);
};
```

---

## 依赖更新

### frontend/package.json

新增依赖:
- `@ag-ui/client`: ^0.20.0
- `@copilotkit/runtime`: ^1.0.0
- `@copilotkit/react-core`: ^1.0.0

---

## 待完成

| 任务 | 状态 | 说明 |
|------|------|------|
| Task 6: 单元测试 | P1 | 待编写 |
| Task 7: 废弃旧端点 | P2 | 待清理 |
| layout.tsx 集成 | - | 项目中未找到 layout.tsx |

---

## 版本记录

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1 | 2026-05-13 | 初始编码实现 |