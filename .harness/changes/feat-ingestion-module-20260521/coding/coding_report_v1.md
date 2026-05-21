# 编码报告 v1

## 基本信息
- 变更ID: feat-ingestion-module-20260521
- 阶段: 编码实现
- 完成时间: 2026-05-21

## 代码统计

| 指标 | 数值 |
|------|------|
| 新增文件 | 5 |
| 修改文件 | 2 |
| 代码行数 | ~800 |
| 测试用例 | 22 |

## 新增文件清单

### backend/app/models/ingestion.py
Pydantic 数据模型定义，包含：
- `TestStepSchema`: 测试步骤模型
- `TestCaseSchema`: 测试用例模型
- `IngestionRequest`: 请求模型
- `IngestionResponse`: 响应模型
- `IngestionErrorResponse`: 错误响应模型

### backend/app/services/document_flattening.py
文档扁平化引擎，包含：
- `DocumentFlatteningEngine`: 主引擎类
- `ExcelFlattener`: Excel 扁平化器
- `MarkdownFlattener`: Markdown 扁平化器

### backend/app/services/ingestion_service.py
LLM 解析服务，包含：
- `IngestionService`: 解析服务类
- `_validate_placeholders()`: 占位符校验
- `_extract_variables_from_text()`: 变量提取
- `parse_markdown()`: Markdown 解析
- `ingest_file()`: 文件解析

### backend/app/api/ingestion.py
API 端点，包含：
- `POST /api/ingestion/file`: 文件上传
- `POST /api/ingestion/markdown`: Markdown 提交
- `POST /api/ingestion/base64`: Base64 编码

### backend/tests/test_ingestion.py
单元测试，包含 22 个测试用例

## 修改文件清单

### backend/app/__init__.py
注册 ingestion router

### backend/pyproject.toml
添加依赖：pandas, openpyxl, pytest-asyncio