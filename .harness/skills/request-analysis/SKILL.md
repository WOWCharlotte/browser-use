---
name: request-analysis
description: 分析用户需求，理解业务逻辑，明确输入输出和边界条件。触发场景：阶段1-需求分析。当用户提出功能需求、bug修复、或技术任务时使用。
---

# 需求分析

## 工作流程

### 1. 理解需求
- 仔细阅读用户需求描述
- 识别核心功能和关键路径
- 确定涉及的模块和组件

### 2. 生成澄清问题（如需要）
- 输入数据的格式和来源
- 输出数据的格式和目的地
- 边界条件和异常场景
- 性能要求
- 依赖关系

### 3. 输出定义
```markdown
## 输入
- 参数1: 类型, 来源, 描述

## 输出
- 返回值: 类型, 格式, 描述
```

### 4. 任务拆分
每个子任务必须包含：目标、范围、输入、输出、验收标准、依赖关系。

## 质量门禁
- spec.md 包含完整的输入输出定义
- 每个子任务有明确的验收标准
- 无模糊的需求描述

## 输出文件
- `.harness/changes/{change-id}/request_analysis/spec.md`
- `.harness/changes/{change-id}/request_analysis/tasks.md`

详细模板和示例见 [references/spec-template.md](references/spec-template.md)
