---
title: 自动化测试工具 - 需求规格说明书
change_id: feat-automated-testing-tool-20260523
phase: 1 - 需求分析
date: 2026-05-23
version: v1.0
---

# 需求规格说明书

## 1. 背景与目标

基于现有 browser-use 项目（FastAPI 后端 + Next.js 前端 + browser-use 库），构建完整的自动化测试工具。现有系统已具备：测试用例解析（ingestion）、Agent 执行引擎、浏览器会话管理、AG-UI 事件流。本需求在此基础上扩展，实现端到端的 GUI 自动化测试平台。

## 2. 用户故事

| # | 用户故事 | 优先级 |
|---|----------|--------|
| US-1 | 上传 Excel/Markdown 文件，LLM 解析为结构化测试用例 | P0 |
| US-2 | 前端展示解析结果，用户可确认/编辑用例 | P0 |
| US-3 | 配置并发数并行执行，每个用例独立浏览器实例 | P0 |
| US-4 | 保存执行轨迹（动作序列 + 截图） | P0 |
| US-5 | LLM 对比实际结果与预期，生成单条评估报告 | P0 |
| US-6 | 全部完成后生成最终报告（HTML + PDF + Excel） | P1 |
| US-7 | 支持混合模式重放（优先录制动作，失败回退 LLM） | P2 |
| US-8 | 人工覆盖评估结果 | P1 |
| US-9 | 选择性执行（指定用例 ID 或重跑失败用例） | P1 |
| US-10 | 历史执行趋势对比 | P2 |

## 3. 功能模块

### 3.1 数据层（Phase 1 - 本次实现）

#### 3.1.1 数据库表设计

**test_plans（测试计划）**
- 字段：id, name, description, source_file_name, max_concurrency, status, created_at, updated_at
- 状态流转：draft → confirmed → running → completed | failed

**test_cases（测试用例）**
- 字段：id, plan_id, case_name, description, module, function_point, start_url, steps_json, global_variables, variable_values_json, status, execution_order, created_at, updated_at
- steps_json 格式：`[{step_number, action_description, expected_result, step_variables, is_visual_checkpoint}]`

**test_case_variable_sets（变量集）**
- 字段：id, case_id, set_index, variables_json, status, created_at
- 支持批量参数化执行

**test_runs（执行运行）**
- 字段：id, plan_id, status, max_concurrency, max_retries, case_timeout_seconds, case_ids_filter, rerun_of_run_id, total_cases, passed_cases, failed_cases, error_cases, started_at, completed_at
- 状态：running | completed | aborted

**test_results（执行结果）**
- 字段：id, run_id, case_id, variable_set_id, session_id, status, actual_result, evaluation, evaluation_details, error_message, duration_seconds, retry_count, case_snapshot_json, original_status, override_reason, trajectory_path, started_at, completed_at
- 状态：pending | running | passed | failed | error

**test_replays（重放记录）**
- 字段：id, result_id, variables_json, status, mode, fallback_count, trajectory_path, started_at, completed_at

#### 3.1.2 Pydantic 模型

**TestStepSchema（扩展）**
- 新增字段：`is_visual_checkpoint: bool = False`

**TestCaseParsedSchema（新增）**
- case_name, description, module, function_point, start_url, steps, global_variables, variable_sets

**TestPlanParsedSchema（新增）**
- test_cases: list[TestCaseParsedSchema]

#### 3.1.3 test_plan_service.py CRUD

- `create_plan(name, description, source_file_name, max_concurrency) -> TestPlanView`
- `get_plan(plan_id) -> TestPlanView | None`
- `list_plans() -> list[TestPlanView]`
- `update_plan(plan_id, **kwargs) -> TestPlanView`
- `delete_plan(plan_id) -> bool`
- `confirm_plan(plan_id) -> TestPlanView`
- `create_case(plan_id, case_data) -> TestCaseView`
- `get_case(case_id) -> TestCaseView | None`
- `list_cases(plan_id) -> list[TestCaseView]`
- `update_case(case_id, **kwargs) -> TestCaseView`
- `delete_case(case_id) -> bool`
- `create_variable_sets(case_id, variable_sets) -> list[VariableSetView]`
- `get_variable_sets(case_id) -> list[VariableSetView]`
- `import_parsed_plan(parsed: TestPlanParsedSchema, name, source_file_name) -> TestPlanView`

#### 3.1.4 API 端点

**测试计划**
- `POST /api/test-plans/upload` — 上传文件解析为测试计划
- `POST /api/test-plans/manual` — 手动输入创建计划
- `GET /api/test-plans` — 列出所有计划
- `GET /api/test-plans/{plan_id}` — 获取计划详情（含用例）
- `PUT /api/test-plans/{plan_id}` — 更新计划
- `DELETE /api/test-plans/{plan_id}` — 删除计划
- `PUT /api/test-plans/{plan_id}/confirm` — 确认计划

**测试用例**
- `POST /api/test-plans/{plan_id}/cases` — 添加用例
- `PUT /api/test-cases/{case_id}` — 编辑用例
- `DELETE /api/test-cases/{case_id}` — 删除用例
- `POST /api/test-cases/{case_id}/variables/import` — 导入变量集
- `GET /api/test-cases/{case_id}/variables` — 获取变量集

### 3.2 解析模块（Phase 2）

扩展现有 `ingestion_service.py`，支持：
- LLM 单步解析+合并（输出 TestPlanParsedSchema）
- 视觉检查点标注（is_visual_checkpoint）
- 多用例拆分与相似用例合并

### 3.3 执行引擎（Phase 4）

- asyncio.Semaphore 并发控制（MAX_CONCURRENCY=5）
- asyncio.wait_for 超时控制（默认 600s）
- 失败重试（仅 error 状态重试，failed 不重试）
- 中断恢复（recover_on_startup）
- DB 写入串行化（asyncio.Queue + writer 协程）
- 与 agent_service 完全隔离

### 3.4 结果评估（Phase 5）

- 检查点模式（仅评估有预期结果的步骤）
- 视觉检查点传入截图给评估 LLM
- 人工覆盖接口

### 3.5 报告生成（Phase 6）

- HTML（Jinja2 模板，含失败截图）
- PDF（Playwright page.pdf()）
- Excel（openpyxl，摘要+详情 sheet）
- 趋势 API

### 3.6 重放功能（Phase 7）

- 封装 Agent.rerun_history()
- 变量替换通过 task prompt 注入
- 混合模式（skip_failures=True + ai_step_llm）

### 3.7 前端界面（Phase 3 + Phase 8）

- 右侧动态面板（panel_mode 切换）
- TestCaseEditor（用例编辑表格）
- ExecutionDashboard（执行进度仪表板）
- TestReport（报告预览 + 下载）
- FileAttachment（Chat 附件上传）

## 4. 非功能需求

| 类别 | 要求 |
|------|------|
| 并发 | 最大 5 个浏览器实例同时运行 |
| 超时 | 单用例默认 600 秒，可配置 |
| 存储 | 轨迹文件 30 天自动清理，单 run 目录 500MB 警告 |
| 可靠性 | 服务重启后自动恢复中断状态 |
| 隔离性 | 测试执行与 agent_service 完全隔离 |
| 数据一致性 | DB 写操作通过 Queue 串行化，避免锁竞争 |

## 5. 约束与依赖

- Python >= 3.11，使用 async/await
- 依赖现有：aiosqlite, FastAPI, browser-use, Playwright
- 新增依赖：openpyxl（Excel 报告），Jinja2（HTML 模板）
- ID 生成：uuid7str
- 后端包管理：uv

## 6. 输入输出定义

### Phase 1 输入
- 用户请求（HTTP API）
- 数据库连接（aiosqlite）

### Phase 1 输出
- 测试计划/用例/变量集的 CRUD 响应（JSON）
- 数据库表结构（5 张新表）
- Pydantic 模型（test_plan.py, test_run.py, test_replay.py）

## 7. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| aiosqlite 并发写入锁竞争 | 写入队列串行化（Phase 4 实现） |
| 浏览器进程泄漏 | 超时后强制 close(force=True) |
| LLM 解析格式不稳定 | Pydantic 严格校验 + 最多 2 次重试 |
| 大文档超出 token 限制 | 分批处理（按 sheet/章节拆分） |
