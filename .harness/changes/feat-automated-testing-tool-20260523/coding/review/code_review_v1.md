---
title: 编码评审报告 v2（修订后）
change_id: feat-automated-testing-tool-20260523
phase: 4 - 编码评审
date: 2026-05-23
reviewer: Expert Reviewer Agent + Owner
result: APPROVED
---

# 编码评审报告 v2（修订后）

## 评审结论

**结论：APPROVED**

v1 评审发现的 3 个 MUST FIX 和 5 个 SHOULD FIX 已全部修复。

## 修复记录

| # | 严重程度 | 问题 | 修复方式 |
|---|----------|------|----------|
| 1 | MUST FIX | SQL 注入风险（动态拼接字段名） | 添加 `_PLAN_UPDATE_FIELDS` 和 `_CASE_UPDATE_FIELDS` 白名单，拼接前验证 |
| 2 | MUST FIX | `init_db()` 连接泄漏 | 用 `try/finally` 包裹，确保 `conn.close()` 必然执行 |
| 3 | MUST FIX | `import_parsed_plan` 非原子操作 | 重写为单连接 + 显式 `BEGIN`/`ROLLBACK` 事务 |
| 4 | SHOULD FIX | `ingestion.py` 使用 `List[...]` 违反规范 | 删除 `from typing import List`，全部改为 `list[...]` |
| 5 | SHOULD FIX | `variable_sets: List[dict]` 类型宽泛 | 改为 `list[dict[str, str]]` |
| 6 | SHOULD FIX | `INTERNAL_ERROR` 暴露 `str(e)` | 改为返回通用消息，详情记录到日志 |
| 7 | SHOULD FIX | `OverrideRequest.status` 无枚举约束 | 改为 `Literal["passed", "failed"]` |
| 8 | SHOULD FIX | `ReplayRequest.mode` 无枚举约束 | 改为 `Literal["hybrid"]` |
| 9 | SHOULD FIX | `import base64` 未使用 | 删除 |

## 附加修复

- `get_db()` 添加 `PRAGMA foreign_keys = ON`，确保级联删除生效
- `_parse_case_row` 中 `json.loads` 添加异常处理，损坏数据不会崩溃

## 验证

```
53 passed in 6.77s
```
