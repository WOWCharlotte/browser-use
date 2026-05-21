# 需求分析文档

## 1. 需求背景

用例接入层是 browser-use 项目的重要组成部分，负责将测试人员编写的测试用例文档（Excel/Markdown 格式）解析为结构化数据，供 Agent 执行自动化测试。

## 2. 功能需求

### 2.1 核心功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Excel 解析 | 支持 .xlsx, .xls 格式，通过 pandas 读取并扁平化为 Markdown | P0 |
| Markdown 解析 | 支持 .md, .markdown 格式，直接读取内容 | P0 |
| LLM 提取 | 使用 LLM structured output 提取步骤和变量 | P0 |
| 变量占位符 | 将测试数据替换为 `{variable}` 格式占位符 | P0 |
| 占位符校验 | 校验 `{}` 正确闭合，支持自动重试 | P0 |
| 文件大小限制 | 最大支持 5MB 文件 | P1 |

### 2.2 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ingestion/parse` | POST | 统一入口：文件上传或 Markdown 内容，自动识别处理 |

## 3. 数据模型

### 3.1 TestStepSchema
```python
{
    "step_number": int,          # >= 1
    "action_description": str,   # 包含 {placeholder}
    "expected_result": str,      # 包含 {placeholder}
    "step_variables": list[str]  # 本步骤变量
}
```

### 3.2 TestCaseSchema
```python
{
    "case_name": str,
    "start_url": str,
    "steps": list[TestStepSchema],
    "global_variables": list[str]  # 全局去重变量
}
```

## 4. 验收标准

| ID | 描述 | 验证方式 |
|----|------|----------|
| AC-1 | Excel 解析后返回 Steps 和 global_variables | 单元测试 |
| AC-2 | 无变量时 global_variables 返回 `[]` | 单元测试 |
| AC-3 | 占位符校验失败自动重试 (最多2次) | 单元测试 |

## 5. 技术约束

- Python >= 3.11
- 使用 `uv` 管理依赖
- 所有 ID 使用 `uuid7str` 生成
- 外部服务调用设置超时