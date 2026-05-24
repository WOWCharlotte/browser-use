---
title: Phase 2-3 单元测试报告
change_id: feat-automated-testing-phase2-3-20260524
phase: 5 - 单元测试编写
date: 2026-05-24
---

# 单元测试报告

## 测试文件

`backend/tests/test_variable_file_parser.py`

## 测试结果

**25/25 通过**（1 个测试因 BOM 双重编码问题修复后通过）

## 覆盖范围

| 测试类别 | 测试数 | 说明 |
|----------|--------|------|
| `_get_extension` | 4 | 正常、大写、无扩展名 |
| `is_supported` | 5 | csv/xlsx/xls/txt/md |
| CSV 解析 | 8 | 正常、UTF-8 BOM、空单元格、空行跳过、无数据行、空表头、非 UTF-8 |
| Excel 解析 | 6 | 正常、空单元格、空行跳过、无数据行、空文件、xls 扩展名 |
| 文件大小限制 | 1 | 超过 2MB 报错 |
| 不支持类型 | 2 | txt、无扩展名 |

## 修复记录

- `test_parse_csv_utf8_bom`：测试用 `"\ufeffname,...".encode("utf-8-sig")` 导致双重 BOM，改为 `"name,...".encode("utf-8-sig")` 正确生成单 BOM 文件

## 前端测试

项目无前端测试框架（package.json 无 vitest/jest），前端组件测试跳过。
