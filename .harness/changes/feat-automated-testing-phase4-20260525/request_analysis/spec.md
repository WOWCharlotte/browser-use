---
title: Phase 4 执行引擎 — 需求规格说明书
change_id: feat-automated-testing-phase4-20260525
phase: 1 - 需求分析
date: 2026-05-25
---

# 需求规格说明书 — Phase 4 执行引擎

## 1. 概述

### 1.1 目标

实现自动化测试工具的执行引擎，支持并行执行测试用例、超时控制、失败重试、中断恢复，并通过 AG-UI 协议实时推送执行进度到前端 ExecutionDashboard 组件。

### 1.2 范围

| 模块 | 内容 |
|------|------|
| 后端服务 | `test_execution_service.py` — 并行执行引擎核心 |
| 后端 API | `test_runs.py` — 执行相关 REST + SSE 端点 |
| AG-UI 扩展 | `agui.py` 支持 STATE_DELTA 事件映射 |
| 前端 Hook | `useStateSnapshot.ts` 扩展 StateDelta 处理 |
| 前端组件 | `ExecutionDashboard.tsx` 及子组件 |
| 日志系统 | `TestCaseLogger` + SSE 日志流端点 |

### 1.3 前置依赖

- Phase 1 数据层（test_runs, test_results 表）✅ 已完成
- Phase 2-3 解析 + 前端面板 ✅ 已完成
- Pydantic 模型 `TestRunCreate`, `TestRunView`, `TestResultView` ✅ 已定义

## 2. 功能需求

### 2.1 执行引擎（test_execution_service.py）

#### 2.1.1 并发控制

- 使用 `asyncio.Semaphore(max_concurrency)` 控制并发
- `max_concurrency` 受 `Config.MAX_CONCURRENCY=5` 硬上限约束
- 每个用例独立浏览器实例，不共享状态

#### 2.1.2 超时控制（P0）

- 使用 `asyncio.wait_for(timeout=case_timeout_seconds)` 包裹单用例执行
- 超时后强制关闭浏览器 `session.close(force=True)`
- 标记结果为 error，记录超时信息

#### 2.1.3 失败重试（P2）

- 仅 `error` 状态（基础设施问题：超时/崩溃）触发重试
- `failed` 状态（功能 bug）不重试
- `max_retries` 配置（默认 1 = 不重试）
- `test_results.retry_count` 记录已重试次数

#### 2.1.4 中断恢复（P0）

- 服务启动时调用 `recover_on_startup()`
- 将所有残留 `running` 状态的 result 标记为 error
- 将所有残留 `running` 状态的 run 标记为 aborted

#### 2.1.5 选择性执行（P1）

- `case_ids` 参数：仅执行指定用例
- `rerun_failed` 参数：从指定 run 中获取 failed/error 的 case_ids 重跑

#### 2.1.6 用例执行流程

1. 快照用例内容到 `test_results.case_snapshot_json`
2. 创建独立 `BrowserSession`（不注册到 agent_service）
3. 变量替换构建 task prompt
4. 创建 `Agent` 并执行 `Agent.run()`
5. 保存轨迹 `agent.save_history(trajectory_path)`
6. 调用评估服务（Phase 5 实现，本阶段 mock）
7. 通过 `on_event` 回调推送状态变更
8. 关闭浏览器

#### 2.1.7 中止执行

- `abort()` 方法取消所有活跃 asyncio.Task
- 强制关闭所有活跃浏览器
- 标记 run 为 aborted，pending 用例标记为 error

### 2.2 API 端点（test_runs.py）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/test-runs` | 启动执行 |
| GET | `/api/test-runs/{run_id}` | 获取运行状态 |
| POST | `/api/test-runs/{run_id}/abort` | 中止执行 |
| GET | `/api/test-runs/{run_id}/results` | 获取所有结果 |
| GET | `/api/test-results/{result_id}/screenshot` | 获取浏览器截图 |
| PUT | `/api/test-results/{result_id}/override` | 人工覆盖评估结果 |
| GET | `/api/test-results/{result_id}/logs` | 获取用例日志（支持 tail=N） |
| GET | `/api/test-results/{result_id}/logs/stream` | SSE 实时日志流 |
| POST | `/api/test-results/{result_id}/retry` | 单条用例重试 |

### 2.3 进度推送（AG-UI 协议扩展）

#### 2.3.1 StateSnapshot（全量）

触发时机：执行开始、执行结束、页面刷新恢复

```json
{
  "type": "STATE_SNAPSHOT",
  "state": {
    "panel_mode": "execution",
    "run_progress": {
      "run_id": "...",
      "total": 10,
      "completed": 0,
      "passed": 0,
      "failed": 0,
      "error": 0,
      "started_at": "2026-05-25T10:00:00Z",
      "status": "running"
    },
    "case_statuses": [...]
  }
}
```

#### 2.3.2 StateDelta（增量）

触发时机：单用例状态变更（高频）

```json
{
  "type": "STATE_DELTA",
  "delta": [
    {"op": "replace", "path": "/run_progress/completed", "value": 3},
    {"op": "replace", "path": "/case_statuses/2/status", "value": "passed"},
    {"op": "replace", "path": "/run_progress/passed", "value": 2}
  ]
}
```

#### 2.3.3 agui.py 扩展

在 `map_agent_event_to_agui` 中添加 STATE_DELTA → `StateDeltaEvent` 映射。

### 2.4 前端组件

#### 2.4.1 useStateSnapshot 扩展

- 新增 `onStateDeltaEvent` 订阅
- 引入 `fast-json-patch` 库应用增量更新
- 保持向后兼容（现有 onStateSnapshotEvent 不变）

#### 2.4.2 ExecutionDashboard 组件树

```
ExecutionDashboard.tsx          -- 容器
├── ExecutionSummaryBar.tsx     -- 进度条 + 指标卡 + 总计时器 + 中止按钮
├── CaseList.tsx                -- 用例列表（原生滚动 + Accordion）
│   └── CaseRow.tsx             -- 单行：名称 + 状态 + 计时器
├── CaseDetail.tsx              -- 展开详情
│   ├── LogStream.tsx           -- SSE 实时日志
│   └── CaseScreenshot.tsx      -- 截图展示
└── ExecutionComplete.tsx       -- 完成汇总 + 报告按钮
```

#### 2.4.3 交互规则

- Accordion 同时只展开一条
- 展开默认显示日志 tab，建立 SSE 连接
- 收起时断开 SSE
- 日志自动滚动，手动上滚暂停
- 中止需确认 popover
- 重试仅 failed/error 可见

### 2.5 日志系统

#### 2.5.1 用例执行日志

- 路径：`data/trajectories/{run_id}/{case_id}_{set_index}.log`
- 格式：结构化文本，每行带时间戳和级别
- 封装：`TestCaseLogger` 类

#### 2.5.2 系统日志

- 路径：`data/logs/test_execution.log`
- 轮转：`RotatingFileHandler`（10MB × 5 files）

## 3. 非功能需求

| 维度 | 要求 |
|------|------|
| 并发上限 | MAX_CONCURRENCY=5 |
| 单用例超时 | 默认 600s，可配置 |
| 轨迹保留 | 30 天自动清理 |
| 日志轮转 | 50MB 总量上限 |
| SSE 心跳 | 20s 间隔保活 |
| 浏览器隔离 | 每用例独立实例，不共享 |

## 4. 输入输出

### 4.1 输入

- `TestRunCreate` 请求体（plan_id, max_concurrency, case_ids, rerun_failed, max_retries, case_timeout_seconds）
- 已确认的测试计划（status=confirmed）中的用例数据

### 4.2 输出

- `TestRunView` — 运行状态
- `TestResultView` — 每条用例执行结果
- StateSnapshot/StateDelta 事件流 — 实时进度
- SSE 日志流 — 用例执行日志
- 轨迹文件 — `data/trajectories/{run_id}/`

## 5. 与现有系统的集成

### 5.1 直接复用

| 模块 | 用途 |
|------|------|
| `browser_service.py` | 创建/关闭浏览器会话 |
| `Config` | LLM 配置、超时配置 |
| `database.py` / `get_db()` | 数据库连接 |
| `uuid7str()` | ID 生成 |
| `Agent` (browser-use) | 执行测试用例 |
| `BrowserSession` | 独立浏览器实例 |

### 5.2 需要扩展

| 文件 | 扩展内容 |
|------|----------|
| `agui.py` | STATE_DELTA 事件映射 + 执行流程集成 |
| `useStateSnapshot.ts` | onStateDeltaEvent 处理 |
| `__init__.py` (app) | 注册 test_runs router + startup 恢复 |
| `TestingPanel.tsx` | execution 模式渲染 ExecutionDashboard |

### 5.3 设计决策（已确认）

| # | 决策 | 结论 |
|---|------|------|
| 1 | 与 agent_service 关系 | 完全独立，直接 import Agent |
| 2 | 进度推送 | StateSnapshot + StateDelta 混合 |
| 3 | DB 写入 | 依赖 aiosqlite 内部锁，不加显式 Queue |
| 4 | 前端数据源 | mount 时 API + snapshot/delta 增量 |
| 5 | 超时清理 | asyncio.wait_for + session.close(force=True) |
| 6 | 虚拟滚动 | MVP 用原生滚动 |
