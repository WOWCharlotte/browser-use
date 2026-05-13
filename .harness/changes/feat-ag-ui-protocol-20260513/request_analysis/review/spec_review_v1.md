# 需求评审报告

## 评审信息

| 字段 | 内容 |
|------|------|
| 变更 ID | feat-ag-ui-protocol-20260513 |
| 评审阶段 | 需求评审 (阶段 2) |
| 评审日期 | 2026-05-13 |
| 评审版本 | v1 |

## 评审议程

1. **需求完整性检查**
2. **任务拆分合理性检查**
3. **技术方案可行性检查**
4. **风险识别**
5. **最终判定**

---

## 1. 需求完整性检查

### 1.1 输入输出定义

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 后端 API 输入定义 | ✅ | `session_id`, `message`, `attachments` |
| RunAgentInput 定义 | ✅ | `threadId`, `messages`, `tools`, `context`, `state`, `forwardedProps` |
| AG-UI 事件定义 | ✅ | 覆盖 lifecycle, message, tool, state, step 五大类 |
| 异常处理定义 | ✅ | LLM 超时、浏览器连接、无效 session、Agent 错误 |

### 1.2 功能列表

| 功能 | 状态 |
|------|------|
| 后端 `/agui` 端点 | ✅ |
| AG-UI BaseEvent SSE 流 | ✅ |
| 生命周期事件 | ✅ |
| 文本消息事件 | ✅ |
| 工具调用事件 | ✅ |
| 步骤事件 | ✅ |
| 状态同步事件 | ✅ |
| HITL 中断机制 | ✅ (已确认) |
| State Sync | ✅ (已确认) |

### 1.3 澄清问题处理

| 问题 | 决策 |
|------|------|
| `/chat` 端点 | 直接废弃 (B) |
| AG-UI 版本 | 0.0.47 (A) |
| 多 Agent | 单 Agent (A) |
| HITL | 必须支持 (A) |
| State Sync | 必须支持 (A) |

---

## 2. 任务拆分合理性检查

### 2.1 任务依赖关系

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
                    Task 7 (废弃旧端点)
```

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 无循环依赖 | ✅ | 单向依赖链清晰 |
| 可并行任务 | ✅ | Task 3 和 Task 4 可并行 |
| 关键路径正确 | ✅ | Task 1 → 2 → 3 → 4 → 5 |
| 任务粒度合理 | ✅ | 每个任务 5-10 个子任务 |

### 2.2 优先级排序

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | Task 1-5 | ✅ 合理 |
| P1 | Task 6 | ✅ 合理 |
| P2 | Task 7 | ✅ 合理（废弃旧端点） |

---

## 3. 技术方案可行性检查

### 3.1 架构设计

| 检查项 | 状态 | 说明 |
|--------|------|------|
| AG-UI 协议兼容性 | ✅ | 使用标准 BaseEvent 类型 |
| CopilotKit 集成 | ✅ | 使用 HttpAgent + copilotRuntimeNextJSAppRouterEndpoint |
| SSE 流式响应 | ✅ | 使用 FastAPI StreamingResponse |
| 事件映射设计 | ✅ | 清晰的自定义事件 → AG-UI 事件映射 |

### 3.2 技术约束

| 约束 | 状态 | 说明 |
|------|------|------|
| Python 3.11+ | ✅ | browser-use 要求 |
| Next.js 14+ | ✅ | App Router 要求 |
| AG-UI 0.0.47+ | ✅ | CopilotKit 要求 |
| @copilotkit/runtime ^1.0.0 | ✅ | 最新稳定版 |

### 3.3 参考实现

通过 CopilotKit MCP 搜索到的参考实现：
- `showcase/integrations/ag2/src/app/api/copilotkit/route.ts`
- `showcase/integrations/pydantic-ai/src/app/api/copilotkit/route.ts`
- `sdks/typescript/packages/client/src/agent/http.ts` (HttpAgent)

---

## 4. 风险识别

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 前端迁移复杂性 | 中 | Task 5 独立，有清晰依赖 |
| 事件映射丢失 | 低 | Task 2 专注事件映射，有详细映射表 |
| AG-UI 版本兼容性 | 低 | 使用稳定版 0.0.47 |
| 测试覆盖率 | 中 | Task 6 专门测试，有 80% 目标 |

---

## 5. 最终判定

### 评审结果

| 项目 | 状态 |
|------|------|
| 需求完整性 | ✅ 通过 |
| 任务拆分 | ✅ 通过 |
| 技术方案 | ✅ 通过 |
| 风险控制 | ✅ 通过 |

### 评审结论

**APPROVED** - 进入阶段 3 (编码实现)

### 后续行动

1. 开始 Task 1: 后端 AG-UI HTTP Agent 端点实现
2. 并行开始 Task 2: Agent Service 改造
3. 更新 summary.md 中的状态

---

## 评审意见处理

| 意见 | 处理结果 |
|------|----------|
| 无阻塞性问题 | - |

### 版本记录

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1 | 2026-05-13 | 初始评审 |