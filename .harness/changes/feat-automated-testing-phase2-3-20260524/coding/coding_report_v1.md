---
title: Phase 2-3 编码报告
change_id: feat-automated-testing-phase2-3-20260524
phase: 3 - 编码实现
date: 2026-05-24
---

# 编码报告 — Phase 2-3

## 变更范围

### Phase 2: 解析增强（已完成）

Phase 2 的核心解析功能（文档解析 + LLM 提取 + 变量合并）已在 Phase 1 中完成。
本次 Phase 2 范围调整为：**变量集通过前端表单填写**，无需文件导入。

**修复**：`ingestion_service.py` 补充 `TestCaseParsedSchema` 导入（`_reconcile_variables` 方法使用了该类型注解但未导入）。

### Phase 3: 前端动态面板

#### 新增文件

| 文件 | 说明 |
|------|------|
| `frontend/src/types/testing.ts` | TypeScript 类型定义（PanelMode, TestCaseView, TestPlanDetailView, TestingSnapshot 等） |
| `frontend/src/components/testing/TestCaseEditor.tsx` | 用例编辑组件（步骤表格 + 变量集表单） |
| `frontend/src/components/testing/TestingPanel.tsx` | 面板容器（根据 panel_mode 切换） |
| `frontend/src/components/testing/index.ts` | 导出索引 |

#### 修改文件

| 文件 | 改动 |
|------|------|
| `frontend/src/lib/api.ts` | 新增 8 个 Testing API 函数 |
| `frontend/src/app/page.tsx` | 右侧面板替换为 TestingPanel，新增 testingSnapshot 状态 |
| `backend/app/services/ingestion_service.py` | 补充 TestCaseParsedSchema 导入 |

## 关键设计决策

### 变量集填写方式
- 用户直接在 `TestCaseEditor` 的变量集表格中填写（点击"添加一行"）
- 填写完成后点击"保存变量集"，调用 `POST /api/test-cases/{id}/variables/import`
- 不需要 CSV/Excel 文件导入

### panel_mode 状态管理
- `panel_mode` 来自 `useStateSnapshot().snapshot.panel_mode`（后端 Agent 推送）
- `page.tsx` 监听 snapshot 变化，当 `panel_mode !== 'browser'` 时切换到 TestingPanel
- 确认计划后重置 testingSnapshot 为 undefined（回到 browser 模式）

### 步骤编辑保存策略
- 300ms 防抖：用户停止输入 300ms 后自动调用 `PUT /api/test-cases/{id}`
- 乐观更新：先更新本地状态，保存失败时显示错误提示
- 使用 `useRef` 管理 timer，避免 stale closure

### TestingPanel 占位符
- `execution` 和 `report` 模式显示占位符，Phase 8 实现完整功能
- 默认（browser 模式）透传所有 BrowserPreview props，不影响现有功能

## 代码质量

- 所有组件有完整 TypeScript 类型
- 无 `any` 类型（除 `as unknown as TestingSnapshot` 的必要类型断言）
- 所有异步操作有 loading 状态和错误处理
- 无障碍：按钮有 `aria-label`，表格有 `role="table"`
