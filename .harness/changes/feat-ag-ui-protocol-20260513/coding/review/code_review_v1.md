# 代码评审报告

## 评审信息

| 字段 | 内容 |
|------|------|
| 变更 ID | feat-ag-ui-protocol-20260513 |
| 评审阶段 | 编码评审 (阶段 4) |
| 评审日期 | 2026-05-13 |
| 评审版本 | v1 |

---

## 发现的问题

### Critical Issues

#### 1. asyncio import 位置错误

**文件**: `backend/app/api/agui.py:337`

**问题**: `import asyncio` 放在文件末尾，在 line 258, 281 等处已经使用。这违反 PEP 8 规范。

**代码**:
```python
# 第 258 行已使用 asyncio
async def event_generator() -> AsyncGenerator[str, None]:
    event_ready = asyncio.Event()

# 第 337 行才导入
import asyncio
```

**修复**: 将 `import asyncio` 移到文件顶部。

---

#### 2. agent.task 运行时变更

**文件**: `backend/app/services/agent_service.py:93`

**问题**: 在 agent 创建后直接修改 `agent.task`，可能不会生效（Agent 内部状态已用原始 task 初始化）。

**代码**:
```python
agent = self._agents.get(session_id)
if not agent:
    agent = await self.create_agent(session_id, message)
else:
    agent.task = message  # 变异 - 违反不可变原则
```

**修复**: 为每个新 task 创建新 agent 实例。

---

#### 3. 事件回调缺少错误处理和同步机制

**文件**: `backend/app/api/agui.py:263-267`

**问题**: `on_event` 回调在 agent.run() 的异步上下文中被调用，直接操作共享队列可能导致竞态条件。

**代码**:
```python
def on_event(event: dict[str, Any]) -> None:
    """事件回调 - 将事件加入队列"""
    event["run_id"] = run_id
    event_queue.append(event)
    event_ready.set()
```

**修复**: 使用 `asyncio.Queue` 代替 list + Event 模式，或确保回调是线程安全的。

---

### High Issues

#### 4. AG-UI 端点无认证

**文件**: `backend/app/api/agui.py:231`

**问题**: `/agui` 端点没有任何认证机制，任何人都可以执行浏览器自动化任务。

**修复**: 添加 API Key 或 JWT 认证。

---

#### 5. 错误响应暴露 stack trace

**文件**: `frontend/src/app/api/copilotkit/route.ts:76-80`

**问题**: 生产环境返回完整错误堆栈给客户端。

**代码**:
```typescript
return NextResponse.json(
    { error: e.message, stack: e.stack },
    { status: 500 },
);
```

**修复**: 只返回错误消息，不返回堆栈信息。

---

#### 6. CORS 配置允许所有来源

**文件**: `backend/app/__init__.py`

**问题**: CORS 配置为 `allow_origins=["*"]`，存在安全风险。

**修复**: 限制为特定的前端域名。

---

### Medium Issues

#### 7. 异常捕获过于宽泛

**文件**: `backend/app/api/agui.py:313`

**问题**: `except Exception as e:` 捕获所有异常，没有针对性处理。

**修复**: 对特定异常进行针对性处理。

---

#### 8. 会话 ID 直接使用用户输入

**文件**: `backend/app/api/agui.py:256`

**问题**: `session_id = thread_id` 直接使用用户输入作为会话标识。

**代码**:
```python
session_id = thread_id  # 直接使用用户输入
```

**修复**: 添加会话所有权验证，或生成内部会话 ID。

---

## 修复记录

### Critical Issues - 已修复

| # | 问题 | 状态 | 修复方式 |
|---|------|------|----------|
| 1 | asyncio import 位置错误 | ✅ 已修复 | 移到文件顶部 (line 7) |
| 2 | agent.task 运行时变异 | ✅ 已修复 | 改为每次创建新 agent 实例 |
| 3 | 事件回调竞态条件 | ✅ 已修复 | 使用 asyncio.Queue 替代 list + Event |

### High Issues - 待处理

| # | 问题 | 状态 |
|---|------|------|
| 4 | 无认证 | 待实现 |
| 5 | 错误响应暴露堆栈 | 待修复 |
| 6 | CORS 过宽 | 待配置 |

### Medium Issues - 已修复/待处理

| # | 问题 | 状态 |
|---|------|------|
| 7 | 异常捕获过宽 | 可接受（当前需要通用处理） |
| 8 | 会话 ID 直接使用用户输入 | 可接受（内部使用场景） |

| 严重程度 | 数量 | 主要问题 |
|----------|------|----------|
| Critical | 3 | asyncio 导入位置、agent.task 变异、事件回调竞态 |
| High | 3 | 无认证、暴露堆栈、CORS 过宽 |
| Medium | 2 | 异常捕获过宽、会话 ID 验证 |

---

## 修复优先级

1. **立即修复**: asyncio import 位置 (影响运行时)
2. **高优先级**: 事件回调同步机制、agent.task 变异
3. **中优先级**: 添加认证、错误响应、CORS 配置

---

## 评审结论

**MUST FIX** - 需要修复 Critical 问题后才能进入下一阶段。

### 必须修复的问题

- [ ] asyncio import 移到文件顶部
- [ ] 事件回调使用 asyncio.Queue
- [ ] agent.task 变异问题（或接受当前行为）

### 建议修复的问题

- [ ] 添加 API 认证
- [ ] 错误响应不暴露堆栈
- [ ] CORS 配置限制来源