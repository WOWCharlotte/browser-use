---
title: 自动化测试工具 - 任务拆解清单（Phase 1）
change_id: feat-automated-testing-tool-20260523
phase: 1 - 需求分析
date: 2026-05-23
---

# 任务拆解清单 — Phase 1：数据层

## 总体范围

Phase 1 实现数据层基础设施：数据库迁移、Pydantic 模型、CRUD 服务、API 端点。

---

## T1: 扩展数据库 init_db()

**文件**: `backend/app/db/database.py`

**目标**: 在现有 `init_db()` 中追加 5 张新表的 CREATE TABLE IF NOT EXISTS SQL

**子任务**:
- [ ] T1.1 添加 `test_plans` 表
- [ ] T1.2 添加 `test_cases` 表（含 FOREIGN KEY → test_plans）
- [ ] T1.3 添加 `test_case_variable_sets` 表（含 FOREIGN KEY → test_cases）
- [ ] T1.4 添加 `test_runs` 表（含 FOREIGN KEY → test_plans）
- [ ] T1.5 添加 `test_results` 表（含 FOREIGN KEY → test_runs, test_cases）
- [ ] T1.6 添加 `test_replays` 表（含 FOREIGN KEY → test_results）
- [ ] T1.7 添加必要索引（plan_id, case_id, run_id）

**验收标准**:
- `init_db()` 执行后 6 张新表存在
- 外键约束正确
- 无 SQL 语法错误

---

## T2: 扩展 config.py

**文件**: `backend/app/config.py`

**目标**: 添加测试工具相关配置项

**子任务**:
- [ ] T2.1 添加 `TRAJECTORY_DIR: Path = PROJECT_ROOT / "data" / "trajectories"`
- [ ] T2.2 添加 `MAX_CONCURRENCY: int = int(os.getenv("MAX_CONCURRENCY", "5"))`
- [ ] T2.3 添加 `CASE_TIMEOUT_SECONDS: int = int(os.getenv("CASE_TIMEOUT_SECONDS", "600"))`
- [ ] T2.4 添加 `TRAJECTORY_RETENTION_DAYS: int = 30`

**验收标准**:
- 配置项可通过环境变量覆盖
- 默认值符合设计文档

---

## T3: 创建 Pydantic 模型文件

### T3.1 扩展 `backend/app/models/ingestion.py`

**目标**: 在现有 TestStepSchema 中添加 `is_visual_checkpoint` 字段，新增 TestCaseParsedSchema 和 TestPlanParsedSchema

**子任务**:
- [ ] T3.1.1 在 `TestStepSchema` 添加 `is_visual_checkpoint: bool = False`
- [ ] T3.1.2 新增 `TestCaseParsedSchema`（含 variable_sets）
- [ ] T3.1.3 新增 `TestPlanParsedSchema`（含 test_cases 列表）

### T3.2 创建 `backend/app/models/test_plan.py`

**目标**: 定义测试计划和用例相关的 View 模型（用于 API 响应）和 Create/Update 请求模型

**子任务**:
- [ ] T3.2.1 `TestPlanView` — 计划响应模型
- [ ] T3.2.2 `TestPlanCreate` — 创建请求模型
- [ ] T3.2.3 `TestPlanUpdate` — 更新请求模型
- [ ] T3.2.4 `TestCaseView` — 用例响应模型（含 steps 解析）
- [ ] T3.2.5 `TestCaseCreate` — 用例创建请求模型
- [ ] T3.2.6 `TestCaseUpdate` — 用例更新请求模型
- [ ] T3.2.7 `VariableSetView` — 变量集响应模型
- [ ] T3.2.8 `VariableImportRequest` — 变量集导入请求模型
- [ ] T3.2.9 `TestPlanDetailView` — 计划详情（含用例列表）

### T3.3 创建 `backend/app/models/test_run.py`

**目标**: 定义执行运行和结果相关模型

**子任务**:
- [ ] T3.3.1 `TestRunView` — 运行响应模型
- [ ] T3.3.2 `TestRunCreate` — 创建请求模型（plan_id, max_concurrency, case_ids?, rerun_failed?）
- [ ] T3.3.3 `TestResultView` — 结果响应模型
- [ ] T3.3.4 `OverrideRequest` — 人工覆盖请求模型

### T3.4 创建 `backend/app/models/test_replay.py`

**目标**: 定义重放相关模型

**子任务**:
- [ ] T3.4.1 `TestReplayView` — 重放响应模型
- [ ] T3.4.2 `ReplayRequest` — 重放请求模型

**验收标准**:
- 所有模型使用 `ConfigDict(extra='forbid')`
- ID 字段使用 `uuid7str`
- 类型注解使用 Python 3.12+ 风格（`str | None` 而非 `Optional[str]`）

---

## T4: 创建 test_plan_service.py

**文件**: `backend/app/services/test_plan_service.py`

**目标**: 实现测试计划和用例的完整 CRUD 操作

**子任务**:
- [ ] T4.1 `create_plan(name, description, source_file_name, max_concurrency) -> TestPlanView`
- [ ] T4.2 `get_plan(plan_id) -> TestPlanView | None`
- [ ] T4.3 `list_plans() -> list[TestPlanView]`
- [ ] T4.4 `update_plan(plan_id, data: TestPlanUpdate) -> TestPlanView`
- [ ] T4.5 `delete_plan(plan_id) -> bool`（级联删除用例和变量集）
- [ ] T4.6 `confirm_plan(plan_id) -> TestPlanView`（draft → confirmed）
- [ ] T4.7 `create_case(plan_id, data: TestCaseCreate) -> TestCaseView`
- [ ] T4.8 `get_case(case_id) -> TestCaseView | None`
- [ ] T4.9 `list_cases(plan_id) -> list[TestCaseView]`
- [ ] T4.10 `update_case(case_id, data: TestCaseUpdate) -> TestCaseView`
- [ ] T4.11 `delete_case(case_id) -> bool`
- [ ] T4.12 `create_variable_sets(case_id, variable_sets: list[dict]) -> list[VariableSetView]`
- [ ] T4.13 `get_variable_sets(case_id) -> list[VariableSetView]`
- [ ] T4.14 `import_parsed_plan(parsed: TestPlanParsedSchema, name, source_file_name) -> TestPlanView`（批量写入）

**验收标准**:
- 所有方法为 async
- 使用 `get_db()` 获取连接，用完关闭
- 错误处理：资源不存在返回 None 或抛出 ValueError
- 日志方法使用 `_log_` 前缀

---

## T5: 创建 API 路由

### T5.1 创建 `backend/app/api/test_plans.py`

**目标**: 实现测试计划和用例的 REST API

**端点清单**:
- [ ] `POST /api/test-plans/upload` — 文件上传解析（multipart/form-data）
- [ ] `POST /api/test-plans/manual` — 手动创建
- [ ] `GET /api/test-plans` — 列表
- [ ] `GET /api/test-plans/{plan_id}` — 详情（含用例）
- [ ] `PUT /api/test-plans/{plan_id}` — 更新
- [ ] `DELETE /api/test-plans/{plan_id}` — 删除
- [ ] `PUT /api/test-plans/{plan_id}/confirm` — 确认
- [ ] `POST /api/test-plans/{plan_id}/cases` — 添加用例
- [ ] `PUT /api/test-cases/{case_id}` — 编辑用例
- [ ] `DELETE /api/test-cases/{case_id}` — 删除用例
- [ ] `POST /api/test-cases/{case_id}/variables/import` — 导入变量集
- [ ] `GET /api/test-cases/{case_id}/variables` — 获取变量集

**验收标准**:
- 参数校验（FastAPI 自动）
- 统一错误响应格式 `{"success": false, "error": "...", "code": "..."}`
- HTTP 状态码正确（404 for not found, 400 for bad request）

### T5.2 注册路由到 `backend/app/__init__.py`

**目标**: 将新路由注册到 FastAPI app

**验收标准**:
- 路由前缀 `/api`
- 不影响现有路由

---

## T6: 编写单元测试

**文件**: `backend/tests/test_test_plan_service.py`

**目标**: 覆盖 test_plan_service 的核心 CRUD 逻辑

**子任务**:
- [ ] T6.1 测试 create_plan / get_plan / list_plans
- [ ] T6.2 测试 update_plan / delete_plan
- [ ] T6.3 测试 confirm_plan 状态流转
- [ ] T6.4 测试 create_case / update_case / delete_case
- [ ] T6.5 测试 create_variable_sets / get_variable_sets
- [ ] T6.6 测试 import_parsed_plan 批量写入
- [ ] T6.7 测试 API 端点（使用 httpx.AsyncClient）

**验收标准**:
- 使用真实 aiosqlite（内存数据库 `:memory:`）
- 不 mock 数据库
- 覆盖率 >= 80%

---

## 依赖关系

```
T1 (DB) → T3 (Models) → T4 (Service) → T5 (API) → T6 (Tests)
T2 (Config) → T4 (Service)
```

## 完成标准

- [ ] 所有 6 张新表在 init_db() 后存在
- [ ] Pydantic 模型通过 pyright 类型检查
- [ ] test_plan_service 所有方法有对应测试
- [ ] API 端点可通过 curl/httpx 调用
- [ ] `uv run pytest tests/test_test_plan_service.py` 全部通过
- [ ] `uv run pyright backend/app/models/test_plan.py` 无错误
