---
title: Phase 2-3 任务拆解清单
change_id: feat-automated-testing-phase2-3-20260524
phase: 1 - 需求分析
date: 2026-05-24
---

# 任务拆解清单 — Phase 2-3

## Phase 2: 解析增强 — 变量集批量导入

### T1: 创建 VariableFileParser 工具类

**文件**: `backend/app/services/variable_file_parser.py`

**子任务**:
- [ ] T1.1 `parse(file_name, file_content) -> list[dict[str, str]]` — 入口方法，按扩展名分发
- [ ] T1.2 `_parse_csv(content: bytes) -> list[dict[str, str]]` — 解析 CSV（UTF-8/UTF-8-BOM）
- [ ] T1.3 `_parse_excel(content: bytes) -> list[dict[str, str]]` — 解析 Excel（openpyxl，取第一 Sheet）
- [ ] T1.4 `is_supported(file_name: str) -> bool` — 检查文件类型
- [ ] T1.5 验证逻辑：文件大小 ≤ 2MB、至少一行数据、表头非空

**验收标准**:
- CSV/Excel 解析正确，空单元格为空字符串
- 不支持的文件类型抛出 `ValueError`
- 无外部依赖（openpyxl 已在 pyproject.toml 中）

---

### T2: 扩展 test_plan_service.py

**文件**: `backend/app/services/test_plan_service.py`

**子任务**:
- [ ] T2.1 新增 `import_variable_sets_from_file(case_id, file_name, file_content) -> list[VariableSetView]`
  - 调用 `VariableFileParser.parse()`
  - 调用现有 `create_variable_sets()`
  - 错误传播（ValueError → 上层处理）

**验收标准**:
- 方法为 async
- 文件解析错误时抛出 ValueError（含描述性消息）

---

### T3: 扩展 API 端点

**文件**: `backend/app/api/test_plans.py`

**子任务**:
- [ ] T3.1 新增 `POST /api/test-cases/{case_id}/variables/import-file` 端点
  - 接受 `file: UploadFile = File(...)`
  - 调用 `test_plan_service.import_variable_sets_from_file()`
  - 返回 `{"success": true, "data": [...], "imported_count": N}`
  - 错误处理：UNSUPPORTED_FILE_TYPE / FILE_TOO_LARGE / EMPTY_FILE / INVALID_FORMAT / NOT_FOUND

**验收标准**:
- multipart/form-data 上传正常工作
- 错误响应格式统一

---

## Phase 3: 前端动态面板

### T4: 创建 TypeScript 类型定义

**文件**: `frontend/src/types/testing.ts`

**子任务**:
- [ ] T4.1 定义 `PanelMode` 类型
- [ ] T4.2 定义 `TestStepView` 接口
- [ ] T4.3 定义 `VariableSetView` 接口
- [ ] T4.4 定义 `TestCaseView` 接口
- [ ] T4.5 定义 `TestPlanView` 接口
- [ ] T4.6 定义 `TestingSnapshot` 接口

**验收标准**:
- 所有字段类型与后端 Pydantic 模型对应
- 使用 `export` 导出所有类型

---

### T5: 扩展 API 客户端

**文件**: `frontend/src/lib/api.ts`

**子任务**:
- [ ] T5.1 `fetchTestPlans(): Promise<TestPlanView[]>`
- [ ] T5.2 `getTestPlan(planId: string): Promise<TestPlanView>`
- [ ] T5.3 `updateTestCase(caseId: string, data: Partial<TestCaseView>): Promise<TestCaseView>`
- [ ] T5.4 `deleteTestCase(caseId: string): Promise<void>`
- [ ] T5.5 `importVariableSetsFromFile(caseId: string, file: File): Promise<VariableSetView[]>`
- [ ] T5.6 `getVariableSets(caseId: string): Promise<VariableSetView[]>`
- [ ] T5.7 `confirmTestPlan(planId: string): Promise<TestPlanView>`
- [ ] T5.8 `uploadTestPlan(file: File, name: string, maxConcurrency?: number): Promise<TestPlanView>`

**验收标准**:
- 所有函数有完整 TypeScript 类型
- 错误处理：非 2xx 响应抛出 Error（含 HTTP 状态码）
- `uploadTestPlan` 使用 FormData

---

### T6: 创建 FileAttachment 组件

**文件**: `frontend/src/components/chat/FileAttachment.tsx`

**子任务**:
- [ ] T6.1 实现文件选择按钮（隐藏 input + 触发点击）
- [ ] T6.2 文件大小验证（> 5MB 显示错误）
- [ ] T6.3 支持的文件类型：`.xlsx,.xls,.md,.markdown`
- [ ] T6.4 `onFileSelect` 回调传递 File 对象
- [ ] T6.5 `disabled` 状态处理（上传中禁用）

**验收标准**:
- 点击按钮触发文件选择
- 超大文件有错误提示
- 有 aria-label 无障碍属性

---

### T7: 创建 TestCaseEditor 组件

**文件**: `frontend/src/components/testing/TestCaseEditor.tsx`

**子任务**:
- [ ] T7.1 用例列表（左侧 1/3）：
  - 显示用例名称、模块、步骤数
  - 点击选中，高亮当前用例
- [ ] T7.2 步骤表格（右侧上半）：
  - 列：序号、操作描述（textarea 可编辑）、预期结果（textarea 可编辑）、视觉检查点（checkbox）
  - 失焦时调用 `updateTestCase` 保存
  - 保存中显示 loading 指示
- [ ] T7.3 变量集表格（右侧下半）：
  - 动态列：变量名为列头
  - 行：每组变量值
  - 空状态：显示"暂无变量集，请导入"
- [ ] T7.4 导入变量集按钮：
  - 触发文件选择（.csv/.xlsx/.xls）
  - 上传成功后刷新变量集列表
  - 失败时显示错误信息
- [ ] T7.5 底部操作栏：
  - "确认计划" 按钮（调用 `confirmTestPlan`）
  - 确认成功后调用 `onConfirm`
  - 确认中显示 loading

**验收标准**:
- 步骤编辑失焦自动保存
- 变量集导入后立即刷新
- 所有异步操作有 loading 状态
- 错误有用户可见的提示

---

### T8: 创建 TestingPanel 容器组件

**文件**: `frontend/src/components/testing/TestingPanel.tsx`

**子任务**:
- [ ] T8.1 接受 `snapshot: TestingSnapshot | undefined` 和 browser props
- [ ] T8.2 `panel_mode === 'case_editor'` → 渲染 `TestCaseEditor`
- [ ] T8.3 `panel_mode === 'execution'` → 渲染占位符（"执行中..."）
- [ ] T8.4 `panel_mode === 'report'` → 渲染占位符（"报告生成中..."）
- [ ] T8.5 其他/undefined → 渲染 `BrowserPreview`（传入现有 props）

**验收标准**:
- panel_mode 切换正确
- BrowserPreview 在默认模式下正常工作
- 占位符有合理的 UI 提示

---

### T9: 改造 page.tsx

**文件**: `frontend/src/app/page.tsx`

**子任务**:
- [ ] T9.1 引入 `TestingPanel` 组件
- [ ] T9.2 从 `useStateSnapshot` 获取 `snapshot`
- [ ] T9.3 将右侧 `BrowserPreview` 替换为 `TestingPanel`（传入 snapshot + browser props）
- [ ] T9.4 `onConfirm` 回调：重置 panel_mode 为 browser（或由后端 snapshot 驱动）

**验收标准**:
- 现有 BrowserPreview 功能不受影响
- snapshot 为 undefined 时默认显示 BrowserPreview

---

### T10: 单元测试

**后端测试文件**: `backend/tests/test_variable_file_parser.py`

**子任务**:
- [ ] T10.1 测试 CSV 解析（正常、UTF-8 BOM、空值）
- [ ] T10.2 测试 Excel 解析（正常、空单元格）
- [ ] T10.3 测试不支持的文件类型
- [ ] T10.4 测试文件大小限制
- [ ] T10.5 测试空数据行
- [ ] T10.6 测试 `import_variable_sets_from_file` 服务方法
- [ ] T10.7 测试 `POST /api/test-cases/{id}/variables/import-file` 端点

**验收标准**:
- 使用真实 aiosqlite（tmp_path DB）
- 不 mock 文件解析
- 覆盖率 >= 80%

---

## 依赖关系

```
T1 (Parser) → T2 (Service) → T3 (API)
T4 (Types) → T5 (API Client) → T6, T7, T8
T7 (Editor) → T8 (Panel) → T9 (page.tsx)
T3 + T8 → T10 (Tests)
```

## 完成标准

- [ ] `uv run pytest tests/test_variable_file_parser.py` 全部通过
- [ ] `pnpm build` 无 TypeScript 错误
- [ ] 上传 CSV/Excel 文件后变量集正确导入
- [ ] 右侧面板根据 panel_mode 正确切换
- [ ] 步骤编辑失焦自动保存
- [ ] 确认计划按钮正常工作
