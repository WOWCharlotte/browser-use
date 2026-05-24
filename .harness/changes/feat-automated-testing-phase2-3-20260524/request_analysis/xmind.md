---
title: Phase 2-3 需求思维导图
change_id: feat-automated-testing-phase2-3-20260524
phase: 1 - 需求分析
date: 2026-05-24
---

# Phase 2-3 需求思维导图

```mermaid
mindmap
  root((自动化测试工具 Phase 2-3))
    Phase2[Phase 2: 解析增强]
      CSV变量集导入
        解析CSV文件
        列名映射为变量名
        行数据映射为变量集
        写入test_case_variable_sets表
      Excel变量集导入
        解析.xlsx/.xls文件
        第一行为表头(变量名)
        后续行为变量值
        支持多Sheet(取第一Sheet)
      API端点
        POST /api/test-cases/{id}/variables/import
        接受multipart/form-data
        返回导入的变量集列表
      数据验证
        变量名必须与用例global_variables匹配
        至少一行数据
        空值处理(空字符串)
    Phase3[Phase 3: 前端动态面板]
      类型定义
        testing.ts
          TestStepView
          TestCaseView
          VariableSetView
          TestPlanView
          TestingSnapshot
          PanelMode枚举
      API客户端扩展
        api.ts扩展
          fetchTestPlans
          getTestPlan
          updateTestCase
          deleteTestCase
          importVariableSets
          confirmTestPlan
          uploadTestPlan
      TestingPanel容器
        根据panel_mode切换面板
        browser模式: 现有BrowserPreview
        case_editor模式: TestCaseEditor
        execution模式: ExecutionDashboard(Phase8)
        report模式: TestReport(Phase8)
      TestCaseEditor组件
        用例列表展示
          用例名称/模块/功能点
          步骤数量/变量数量
          状态标签
        步骤编辑
          步骤序号/操作描述/预期结果
          变量占位符高亮
          视觉检查点标记
        变量集管理
          变量集表格展示
          CSV/Excel文件上传导入
          手动添加变量集
        操作按钮
          确认计划(confirm)
          删除用例
          添加用例
      FileAttachment组件
        Chat输入框旁附件按钮
        支持.xlsx/.xls/.md/.markdown
        文件大小限制5MB
        上传后触发解析流程
      page.tsx改造
        右侧区域根据panel_mode切换
        TestingPanel或BrowserPreview
      useStateSnapshot扩展
        支持TestingSnapshot类型
        panel_mode字段解析
        test_plan字段解析
```
