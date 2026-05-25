---
title: Phase 4 执行引擎 — 任务拆解清单
change_id: feat-automated-testing-phase4-20260525
phase: 1 - 需求分析
date: 2026-05-25
---

# 任务拆解清单 — Phase 4 执行引擎

## T1: 扩展 agui.py 支持 STATE_DELTA 事件

**文件**: `backend/app/api/agui.py`

**子任务**:
- [ ] T1.1 导入 `StateDeltaEvent` from ag_ui.core（若不存在则用 CustomEvent 降级）
- [ ] T1.2 在 `map_agent_event_to_agui` 中添加 `STATE_DELTA` 分支
- [ ] T1.3 验证 delta 格式为 JSON Patch 数组

**验收标准**:
- STATE_DELTA 事件正确映射为 AG-UI 协议事件
- 不影响现有事件映射逻辑

---

## T2: 扩展 useStateSnapshot hook

**文件**: `frontend/src/hooks/useStateSnapshot.ts`

**子任务**:
- [ ] T2.1 安装 `fast-json-patch` 依赖
- [ ] T2.2 在 subscriber 中添加 `onStateDeltaEvent` 处理
- [ ] T2.3 使用 `applyPatch` 将 delta 合并到当前 state
- [ ] T2.4 保持 `onStateSnapshotEvent` 逻辑不变（向后兼容）

**验收标准**:
- StateDelta 事件正确应用到 snapshot 状态
- 现有 StateSnapshot 功能不受影响
- TypeScript 类型正确

---

## T3: 实现 TestCaseLogger 日志封装

**文件**: `backend/app/services/test_case_logger.py`

**子任务**:
- [ ] T3.1 `TestCaseLogger` 类：接受 run_id, case_id, set_index
- [ ] T3.2 创建独立 FileHandler 写入 `data/trajectories/{run_id}/{case_id}_{set_index}.log`
- [ ] T3.3 提供 `info()`, `warn()`, `error()` 方法（带时间戳格式化）
- [ ] T3.4 `close()` 方法关闭 handler
- [ ] T3.5 确保目录自动创建

**验收标准**:
- 日志文件按规则命名
- 每行格式：`[2026-05-25 10:00:00] [INFO] message`
- close 后不再写入

---

## T4: 实现 test_execution_service.py 核心引擎

**文件**: `backend/app/services/test_execution_service.py`

**子任务**:
- [ ] T4.1 `TestExecutionService` 类骨架 + 单例
- [ ] T4.2 `recover_on_startup()` — 清理残留 running 状态
- [ ] T4.3 `start_run()` — 创建 run 记录、展开变量集、启动并发执行
- [ ] T4.4 `_get_executable_cases()` — 获取待执行用例（支持 case_ids 过滤 + rerun_failed）
- [ ] T4.5 `_execute_case()` — 单用例执行（含超时、重试循环）
- [ ] T4.6 `_execute_case_inner()` — 实际执行逻辑（BrowserSession + Agent + 轨迹保存）
- [ ] T4.7 `_build_task_prompt()` — 变量替换构建 prompt
- [ ] T4.8 `abort_run()` — 中止执行（取消 tasks + 关闭浏览器）
- [ ] T4.9 `retry_result()` — 单条用例重试
- [ ] T4.10 `_emit_snapshot()` / `_emit_delta()` — 进度推送辅助方法
- [ ] T4.11 `_update_run_stats()` — 更新 run 统计数字
- [ ] T4.12 `_cleanup_old_trajectories()` — 30 天轨迹清理

**验收标准**:
- 并发数受 MAX_CONCURRENCY 约束
- 超时后浏览器被强制关闭
- error 状态触发重试，failed 不重试
- 服务启动时残留状态被清理
- on_event 回调正确推送 StateSnapshot 和 StateDelta

---

## T5: 实现 test_runs.py API 路由

**文件**: `backend/app/api/test_runs.py`

**子任务**:
- [ ] T5.1 `POST /api/test-runs` — 启动执行
- [ ] T5.2 `GET /api/test-runs/{run_id}` — 获取运行状态
- [ ] T5.3 `POST /api/test-runs/{run_id}/abort` — 中止执行
- [ ] T5.4 `GET /api/test-runs/{run_id}/results` — 获取所有结果
- [ ] T5.5 `GET /api/test-results/{result_id}/screenshot` — 获取截图
- [ ] T5.6 `PUT /api/test-results/{result_id}/override` — 人工覆盖
- [ ] T5.7 `GET /api/test-results/{result_id}/logs` — 获取日志（支持 tail=N）
- [ ] T5.8 `GET /api/test-results/{result_id}/logs/stream` — SSE 实时日志流
- [ ] T5.9 `POST /api/test-results/{result_id}/retry` — 单条重试

**验收标准**:
- 所有端点返回统一格式 `{"success": true/false, "data": ...}`
- SSE 端点正确设置 Content-Type 和 Cache-Control
- 错误处理完善（NOT_FOUND, INVALID_STATE 等）

---

## T6: 集成 agui.py 执行流程

**文件**: `backend/app/api/agui.py`

**子任务**:
- [ ] T6.1 识别"执行测试"意图（用户消息匹配）
- [ ] T6.2 调用 `test_execution_service.start_run()` 并传入 `on_event` 回调
- [ ] T6.3 将执行引擎事件通过 encoder 推送到 SSE 流
- [ ] T6.4 执行完成后推送 panel_mode=report 的 StateSnapshot

**验收标准**:
- 用户在 chat 中发送执行指令后触发执行
- 执行进度实时推送到前端
- 执行完成后自动切换到报告面板

---

## T7: 实现 ExecutionDashboard 前端组件

**文件**: `frontend/src/components/testing/ExecutionDashboard.tsx` 及子组件

**子任务**:
- [ ] T7.1 `ExecutionDashboard.tsx` — 容器组件，管理整体状态
- [ ] T7.2 `ExecutionSummaryBar.tsx` — 进度条 + 指标卡 + 总计时器 + 中止按钮
- [ ] T7.3 `CaseList.tsx` — 用例列表（原生滚动）
- [ ] T7.4 `CaseRow.tsx` — 单行：名称 + 状态标签 + 计时器
- [ ] T7.5 `CaseDetail.tsx` — Accordion 展开内容（tab 切换）
- [ ] T7.6 `LogStream.tsx` — SSE 实时日志（自动滚动 + 暂停）
- [ ] T7.7 `CaseScreenshot.tsx` — 按需拉取截图
- [ ] T7.8 `ExecutionComplete.tsx` — 完成汇总 + 查看报告按钮

**验收标准**:
- 进度条实时更新
- 状态标签颜色正确（pending=gray, running=blue, passed=green, failed=red, error=orange）
- Accordion 同时只展开一条
- 日志 SSE 连接管理正确（展开连接、收起断开）
- 中止按钮有确认 popover
- 重试按钮仅 failed/error 可见

---

## T8: 注册路由 + 启动恢复

**文件**: `backend/app/__init__.py` 或 `backend/app/main.py`

**子任务**:
- [ ] T8.1 注册 `test_runs.router` 到 FastAPI app
- [ ] T8.2 在 startup 事件中调用 `test_execution_service.recover_on_startup()`
- [ ] T8.3 在 startup 事件中调用 `_cleanup_old_trajectories()`

**验收标准**:
- 服务启动时自动恢复残留状态
- 新路由可访问

---

## T9: TestingPanel 集成

**文件**: `frontend/src/components/testing/TestingPanel.tsx`

**子任务**:
- [ ] T9.1 `panel_mode === 'execution'` 时渲染 `ExecutionDashboard`
- [ ] T9.2 传入 snapshot 中的 `run_progress` 和 `case_statuses`
- [ ] T9.3 处理 mount 时的初始数据加载（API 获取完整状态）

**验收标准**:
- 面板模式切换正确
- 页面刷新后能恢复执行状态

---

## 依赖关系

```
T1 (agui STATE_DELTA) ─┐
T2 (useStateSnapshot)  ─┤
T3 (TestCaseLogger)    ─┼→ T4 (执行引擎) → T5 (API) → T6 (agui 集成)
                        │
                        └→ T7 (前端组件) → T9 (TestingPanel 集成)
                        
T8 (路由注册) 依赖 T4 + T5
```

## 完成标准

- [ ] `uv run pytest backend/tests/test_execution_service.py` 全部通过
- [ ] `pnpm build` 无 TypeScript 错误
- [ ] 启动执行后前端实时显示进度
- [ ] 超时用例被正确标记为 error
- [ ] 中止执行后所有浏览器关闭
- [ ] SSE 日志流正常工作
- [ ] 服务重启后残留状态被清理
