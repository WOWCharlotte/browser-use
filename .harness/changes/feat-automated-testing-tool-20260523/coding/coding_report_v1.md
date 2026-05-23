---
title: 编码报告 v1
change_id: feat-automated-testing-tool-20260523
phase: 3 - 编码实现
date: 2026-05-23
---

# 编码报告 v1

## 实现范围

Phase 1 数据层，包含以下文件：

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/db/database.py` | 修改 | 添加 6 张新表 + 6 个索引 |
| `backend/app/config.py` | 修改 | 添加 4 个配置项 |
| `backend/app/models/ingestion.py` | 修改 | 添加 `is_visual_checkpoint` 字段 + 2 个新模型 |
| `backend/app/models/test_plan.py` | 新建 | 9 个 Pydantic 模型 |
| `backend/app/models/test_run.py` | 新建 | 4 个 Pydantic 模型 |
| `backend/app/models/test_replay.py` | 新建 | 2 个 Pydantic 模型 |
| `backend/app/services/test_plan_service.py` | 新建 | 14 个 async 方法 |
| `backend/app/api/test_plans.py` | 新建 | 12 个 API 端点 |
| `backend/app/api/__init__.py` | 修改 | 注册新路由 |
| `backend/backend/pyproject.toml` | 修改 | 添加 pytest 配置 |
| `backend/tests/test_test_plan_service.py` | 新建 | 37 个测试用例 |

## 关键实现细节

### 数据库层
- 6 张新表全部使用 `CREATE TABLE IF NOT EXISTS`，幂等安全
- 外键约束：test_cases → test_plans（CASCADE），test_case_variable_sets → test_cases（CASCADE）
- 6 个索引覆盖所有外键字段

### 模型层
- 所有模型使用 `ConfigDict(extra='forbid')`
- 类型注解使用 Python 3.12+ 风格（`str | None`）
- `TestStepSchema.is_visual_checkpoint` 向后兼容（默认 False）

### 服务层
- 所有方法为 async，使用 `get_db()` 获取连接，finally 块关闭
- `update_plan/update_case` 使用动态 SQL 构建，只更新非 None 字段
- `import_parsed_plan` 批量写入，按顺序创建用例和变量集
- 日志方法统一使用 `_log_` 前缀

### API 层
- 统一错误响应格式：`{"success": false, "error": "...", "code": "..."}`
- HTTP 状态码：404 for not found，400 for bad request，500 for internal error
- 文件上传端点复用现有 `ingestion_service`，包装为 `TestPlanParsedSchema`

## 验证结果

```
37 passed in 5.73s
```

所有测试通过，包括：
- TestPlanService CRUD（20 个测试）
- 变量集管理（3 个测试）
- 批量导入（3 个测试）
- API 端点（11 个测试）
