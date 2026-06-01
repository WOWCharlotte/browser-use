# Multi-Agent Architecture Design

**Date**: 2026-06-01
**Topic**: Extend single-agent ChatWindow into a hierarchical multi-agent system

---

## Status

Explored — pending user approval

---

## 1. Overview

Extend the current single-agent chat interface into a **hierarchical multi-agent system** where:

- A **MasterAgent** understands user intent, fills missing information, and routes tasks
- **Sub-agents** are specialized workers created per task and discarded after use
- All agents communicate via a shared `bubus` event bus
- Events are mapped to AG-UI protocol and streamed to the frontend via SSE
- Frontend renders all agents in a **single shared chat window** with distinct visual roles

---

## 2. User Experience

### 2.1 Interaction Flow

```
User: "我想测试登录功能"
    ↓
MasterAgent (规划师): "好的，请上传测试用例文件（Excel 或 Markdown）"
    ↓
User: [上传 Excel 文件]
    ↓
MasterAgent (路由): 识别附件 → 派发给 TestPlannerAgent
    ↓
TestPlannerAgent (构建师): 解析文件 → 提取测试用例结构
    ↓ [通过 bubus 总线事件汇回]
    ↓
MasterAgent: "已提取 3 个测试用例，请在右侧确认后可编辑，完成后点击「确认计划」"
    ↓
User: "确认计划"
    ↓
TestExecutionAgent (执行者): 驱动浏览器执行测试步骤
    ↓ [执行完成，自动链式触发]
TestEvaluatorAgent (评估师): 评估结果 → 输出判定报告
    ↓ [通过 bubus 总线事件汇回]
    ↓
MasterAgent: [展示最终报告]
```

### 2.2 Frontend — Single Chat Window with Agent Roles

All agents share one chat stream. Messages are styled by source agent:

| Agent | Visual Style |
|-------|-------------|
| MasterAgent (规划师) | 蓝色气泡，图标为 🤖 |
| TestPlannerAgent (构建师) | 绿色气泡，图标为 📝 |
| TestExecutionAgent (执行者) | 橙色气泡，图标为 🌐 |
| TestEvaluatorAgent (评估师) | 紫色气泡，图标为 ✅ |
| User | 灰色气泡 |

System events (routing decisions, state snapshots) render as subtle inline annotations.

---

## 3. Agent Design

### 3.1 Sub-Agent Registry

| Sub-Agent | Trigger | Dies After | Auto-chain |
|-----------|---------|-----------|------------|
| **TestPlannerAgent** | MasterAgent detects file attachment or user edit request | Plan confirmed | No — waits for user confirmation |
| **TestExecutionAgent** | User confirms plan | All cases executed | No — requires user confirmation |
| **TestEvaluatorAgent** | TestExecutionAgent completes | Evaluation complete | **Yes — auto-triggered after execution** |

Each sub-agent is **stateless** — created fresh per routing, disposed after completion.

### 3.2 MasterAgent — Routing Rules

MasterAgent uses a **rule engine with LLM fallback**:

```
MATCH conditions (evaluated in order):
  1. message has file attachment OR user edit request → TestPlannerAgent
  2. session has draft plan AND message matches "确认|开始执行|run" → TestExecutionAgent
  3. session has executed plan AND auto_trigger enabled → TestEvaluatorAgent (auto-chain)
  4. otherwise → LLM fallback (ask clarifying questions)
```

LLM fallback is used only when rules don't match. MasterAgent then asks:
> "我需要更多信息：要测试的是什么场景？有没有现有的测试用例文件？"

### 3.3 Routing State Machine

MasterAgent tracks session-level routing state to enforce sequence:

```
idle
  │
  ├── [file attached] → planning → planned
  │                                │
  │                                ├── [user confirms] → executing → executed
  │                                │                          │
  │                                │                          └── [auto-chain] → evaluating → evaluated
  │                                │                                              │
  └── [other input] → LLM引导 ←───────────────────────────────────────────────────┘
```

Invalid transitions are rejected (e.g., cannot execute before plan is confirmed).

---

## 4. Architecture

### 4.1 Component Map

```
User Input (HTTP)
    ↓
agui_endpoint (entry point)
    ↓
MasterAgent
    ├─ rule_engine.py: pattern match → routing decision
    ├─ llm_router.py: LLM fallback for ambiguous input
    └─ session_state.py: routing state machine
    ↓ [creates sub-agent]
TestParserAgent / TestExecutionAgent / TestEvaluatorAgent
    ↓ [publish events to bubus]
bubus Event Bus (shared, single-process)
    ↓ [event subscription]
Event Mapper (map_agent_event_to_agui)
    ↓
SSE Stream → Frontend
```

### 4.2 New Backend Files

| File | Responsibility |
|------|----------------|
| `app/agents/master.py` | MasterAgent: rule engine + session state + LLM fallback |
| `app/agents/rules.py` | Routing rules definition |
| `app/agents/sub/test_planner.py` | TestPlannerAgent implementation |
| `app/agents/sub/test_execution.py` | TestExecutionAgent implementation |
| `app/agents/sub/test_evaluator.py` | TestEvaluatorAgent implementation |
| `app/agents/registry.py` | Sub-agent factory + lifecycle management |
| `app/agents/events.py` | Shared event types for inter-agent communication |
| `backend/app/api/agui.py` | Minimal entry point — delegates to MasterAgent |

### 4.3 bubus Event Bus Extension

Current: single consumer (`map_agent_event_to_agui`).

Extended: multiple agents subscribe to the same bus. Each event carries a `source_agent` field so subscribers can filter:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class AgentEvent:
    source_agent: Literal["master", "parser", "execution", "evaluator"]
    event_type: str
    payload: dict

# Sub-agents publish with their identity
await event_bus.publish(AgentEvent(
    source_agent="parser",
    event_type="STEP_FINISHED",
    payload={"step_name": "解析文件", "cases_found": 3}
))

# MasterAgent subscribes to all events
event_bus.subscribe(lambda e: handle_sub_agent_event(e), source_agent="*")
```

### 4.4 Event Mapping

Events from sub-agents flow through the existing `map_agent_event_to_agui` unchanged. The `source_agent` field is embedded in the event payload and used by the frontend for styling.

### 4.5 MasterAgent → agui_endpoint Relationship

`agui_endpoint` becomes a thin wrapper:

```python
@router.post("/agui")
async def agui_endpoint(input_data: RunAgentInput, request: Request) -> StreamingResponse:
    # Minimal: extract session_id, pass to MasterAgent
    master = MasterAgent(session_id=session_id, on_event=on_event)
    return await master.run(input_data)
```

All routing logic moves into `MasterAgent`.

### 4.6 Chain Trigger — Execution → Evaluation

TestEvaluatorAgent is triggered automatically when TestExecutionAgent completes:

```
TestExecutionAgent finishes all cases
    ↓
emits "EXECUTION_COMPLETED" event on bubus
    ↓
MasterAgent intercepts event → auto-creates TestEvaluatorAgent
    ↓
TestEvaluatorAgent runs → results flow back to SSE
```

This is a direct event subscription, not a MasterAgent routing decision.

---

## 5. Frontend Changes

### 5.1 Agent Role Styling

Extend ChatWindow to read `source_agent` from SSE events and apply CSS class:

```typescript
const roleStyles: Record<string, string> = {
  master:     "border-blue-400 bg-blue-50 text-blue-900",
  parser:     "border-green-400 bg-green-50 text-green-900",
  execution:  "border-orange-400 bg-orange-50 text-orange-900",
  evaluator:  "border-purple-400 bg-purple-50 text-purple-900",
  user:       "border-gray-400 bg-gray-50 text-gray-900",
};
```

### 5.2 State Snapshot Extension

`StateSnapshotEvent` payload gains a `source_agent` field so the frontend knows which agent triggered a state change.

### 5.3 No UI Panel Changes

Single chat window handles all interactions. The execution dashboard (`TestingPanel`, `TestCaseEditor`) is unaffected — it receives its data from polling, not from the chat stream.

---

## 6. Implementation Order

### Phase 1 — Core Infrastructure
1. Define `AgentEvent` dataclass + event bus multi-subscriber extension
2. Implement `MasterAgent` rule engine (no LLM, hardcoded patterns)
3. Implement `MasterAgent` session state machine
4. Update `agui_endpoint` to delegate to MasterAgent
5. Wire up event bus → SSE pipeline (verify existing events still work)

### Phase 2 — First Sub-Agent
6. Implement `TestPlannerAgent` (rename from extracted `ingestion_service` logic)
7. Wire TestPlannerAgent into MasterAgent routing
8. Frontend: add role styling to ChatWindow
9. End-to-end test: upload file → see planner events in chat

### Phase 3 — Remaining Sub-Agents
10. Implement `TestExecutionAgent` (extracted from `test_execution_service`)
11. Implement `TestEvaluatorAgent` (extracted from `test_evaluation_service`)
12. Wire routing state machine enforcement
13. LLM fallback for ambiguous input

### Phase 4 — Polish
14. LLM-powered clarifying questions in MasterAgent
15. Visual polish: agent icons, animations
16. Error recovery: what happens when a sub-agent crashes mid-execution?

---

## 7. Open Questions

| Question | Decision Needed |
|----------|----------------|
| Should MasterAgent ask LLM to generate clarifying questions, or use templates? | Templates first (simpler), LLM later |
| How does the frontend know when to switch between chat and execution dashboard? | `panel_mode` in StateSnapshotEvent |
| What happens if user sends a message while a sub-agent is running? | Queue or reject with "请等待当前任务完成" |
| Session state persistence across restarts? | DB-backed state machine (out of scope for v1) |

---

## 8. Backward Compatibility

- `agui_endpoint` remains at the same path — no breaking changes to callers
- Existing `map_agent_event_to_agui` continues to work unchanged
- Frontend `ChatWindow` adds styling without removing existing behavior
- All existing services (`ingestion_service`, `test_execution_service`, etc.) are unchanged — sub-agents delegate to them internally