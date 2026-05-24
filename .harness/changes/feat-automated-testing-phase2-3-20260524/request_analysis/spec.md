---
title: Phase 2-3 需求规格说明书
change_id: feat-automated-testing-phase2-3-20260524
phase: 1 - 需求分析
date: 2026-05-24
---

# 需求规格说明书 — Phase 2-3

## 1. 背景

Phase 1 已完成数据层（6张表、CRUD服务、API端点）。Phase 2 实现变量集的批量导入（CSV/Excel），Phase 3 实现前端动态面板（TestingPanel + TestCaseEditor + 附件上传）。

## 2. Phase 2: 解析增强 — 变量集批量导入

### 2.1 功能描述

允许用户通过上传 CSV 或 Excel 文件，批量导入测试用例的变量集（参数化数据）。

### 2.2 输入规格

**CSV 格式**：
- 第一行：表头，列名即变量名（与用例 `global_variables` 对应）
- 后续行：每行一组变量值
- 编码：UTF-8（带或不带 BOM）
- 示例：
  ```csv
  user_phone,sms_code,user_nickname
  13800138001,123456,测试用户A
  13900139002,654321,测试用户B
  ```

**Excel 格式**：
- 支持 `.xlsx` 和 `.xls`
- 取第一个 Sheet
- 第一行：表头（变量名）
- 后续行：变量值
- 空单元格处理为空字符串

### 2.3 API 端点

**现有端点扩展**：`POST /api/test-cases/{case_id}/variables/import`

当前实现接受 JSON body（`VariableImportRequest`），需扩展为同时支持：
1. JSON body（现有，保持兼容）
2. multipart/form-data 文件上传（新增）

**新增端点**：`POST /api/test-cases/{case_id}/variables/import-file`
- Content-Type: multipart/form-data
- 参数：`file: UploadFile`（.csv / .xlsx / .xls）
- 响应：`{"success": true, "data": [VariableSetView], "imported_count": N}`

### 2.4 服务层扩展

在 `test_plan_service.py` 中新增：

```python
async def import_variable_sets_from_file(
    self,
    case_id: str,
    file_name: str,
    file_content: bytes,
) -> list[VariableSetView]
```

内部调用新增的 `VariableFileParser` 工具类（`backend/app/services/variable_file_parser.py`）：

```python
class VariableFileParser:
    def parse(self, file_name: str, file_content: bytes) -> list[dict[str, str]]
    def _parse_csv(self, content: bytes) -> list[dict[str, str]]
    def _parse_excel(self, content: bytes) -> list[dict[str, str]]
```

### 2.5 验证规则

1. 文件类型：仅支持 `.csv`、`.xlsx`、`.xls`
2. 文件大小：≤ 2MB
3. 至少一行数据（不含表头）
4. 表头不能为空
5. 空值处理：空单元格 → 空字符串（不报错）

### 2.6 错误响应

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `UNSUPPORTED_FILE_TYPE` | 400 | 文件类型不支持 |
| `FILE_TOO_LARGE` | 400 | 文件超过 2MB |
| `EMPTY_FILE` | 400 | 文件无数据行 |
| `INVALID_FORMAT` | 400 | 文件格式错误（无表头等） |
| `NOT_FOUND` | 404 | 用例不存在 |

---

## 3. Phase 3: 前端动态面板

### 3.1 功能描述

在现有三列布局（Sidebar + Chat + 右侧面板）基础上，右侧面板根据 `StateSnapshot.panel_mode` 动态切换内容。Phase 3 实现 `case_editor` 模式（用例编辑）和附件上传能力。

### 3.2 TypeScript 类型定义

**文件**：`frontend/src/types/testing.ts`

```typescript
export type PanelMode = 'browser' | 'case_editor' | 'execution' | 'report';

export interface TestStepView {
  step_number: number;
  action_description: string;
  expected_result: string | null;
  step_variables: string[];
  is_visual_checkpoint: boolean;
}

export interface VariableSetView {
  id: string;
  set_index: number;
  variables: Record<string, string>;
}

export interface TestCaseView {
  id: string;
  plan_id: string;
  case_name: string;
  description: string | null;
  module: string | null;
  function_point: string | null;
  start_url: string;
  steps: TestStepView[];
  global_variables: string[];
  status: string;
  execution_order: number | null;
  created_at: string;
  updated_at: string;
}

export interface TestPlanView {
  id: string;
  name: string;
  description: string | null;
  source_file_name: string | null;
  max_concurrency: number;
  status: string;
  created_at: string;
  updated_at: string;
  cases: TestCaseView[];
}

export interface TestingSnapshot {
  panel_mode: PanelMode;
  test_plan?: TestPlanView;
  run_progress?: {
    run_id: string;
    total: number;
    completed: number;
    passed: number;
    failed: number;
  };
  case_statuses?: Array<{
    result_id: string;
    case_id: string;
    case_name: string;
    status: 'pending' | 'running' | 'passed' | 'failed' | 'error';
  }>;
  report_url?: string;
}
```

### 3.3 API 客户端扩展

**文件**：`frontend/src/lib/api.ts` 新增函数：

| 函数 | 方法 | 路径 |
|------|------|------|
| `fetchTestPlans()` | GET | `/api/test-plans` |
| `getTestPlan(planId)` | GET | `/api/test-plans/{id}` |
| `updateTestCase(caseId, data)` | PUT | `/api/test-cases/{id}` |
| `deleteTestCase(caseId)` | DELETE | `/api/test-cases/{id}` |
| `importVariableSetsFromFile(caseId, file)` | POST | `/api/test-cases/{id}/variables/import-file` |
| `getVariableSets(caseId)` | GET | `/api/test-cases/{id}/variables` |
| `confirmTestPlan(planId)` | PUT | `/api/test-plans/{id}/confirm` |
| `uploadTestPlan(file, name, maxConcurrency)` | POST | `/api/test-plans/upload` |

### 3.4 组件结构

```
frontend/src/components/testing/
  TestingPanel.tsx      — 容器，根据 panel_mode 切换
  TestCaseEditor.tsx    — 用例编辑表格（含步骤、变量集）
frontend/src/components/chat/
  FileAttachment.tsx    — Chat 附件按钮
```

### 3.5 TestingPanel 组件

**职责**：根据 `snapshot.panel_mode` 渲染不同面板。

**Props**：
```typescript
interface TestingPanelProps {
  snapshot: TestingSnapshot | undefined;
  onConfirm: () => void;
}
```

**行为**：
- `panel_mode === 'browser'` 或 `undefined`：渲染 `BrowserPreview`（传入现有 props）
- `panel_mode === 'case_editor'`：渲染 `TestCaseEditor`
- `panel_mode === 'execution'`：渲染占位符（Phase 8 实现）
- `panel_mode === 'report'`：渲染占位符（Phase 8 实现）

### 3.6 TestCaseEditor 组件

**职责**：展示和编辑测试计划中的用例。

**Props**：
```typescript
interface TestCaseEditorProps {
  plan: TestPlanView;
  onConfirm: () => void;
  onPlanUpdate: (plan: TestPlanView) => void;
}
```

**功能**：
1. 用例列表（左侧）：显示用例名称、模块、步骤数
2. 用例详情（右侧）：
   - 步骤表格：序号、操作描述（可编辑）、预期结果（可编辑）、视觉检查点（checkbox）
   - 变量集表格：变量名列 + 每组值
   - 导入变量集按钮（触发文件选择）
3. 底部操作栏：
   - "确认计划" 按钮（调用 `confirmTestPlan`，触发 `onConfirm`）
   - 步骤编辑后自动调用 `updateTestCase` 保存

**编辑保存策略**：
- 步骤编辑：失焦时调用 `PUT /api/test-cases/{id}` 保存（不通过 RESUME 传数据）
- 变量集导入：文件选择后立即上传，成功后刷新变量集列表

### 3.7 FileAttachment 组件

**职责**：在 Chat 输入框旁提供文件上传按钮，上传测试用例文件。

**Props**：
```typescript
interface FileAttachmentProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  disabled?: boolean;
}
```

**行为**：
- 点击触发文件选择（`<input type="file" accept=".xlsx,.xls,.md,.markdown">`）
- 选择后调用 `onFileSelect` 回调
- 文件大小超过 5MB 时显示错误提示

### 3.8 page.tsx 改造

**改动**：
1. 引入 `TestingPanel` 组件
2. 从 `useStateSnapshot` 获取 `snapshot`
3. 判断 `snapshot?.panel_mode`：
   - 非 `case_editor`/`execution`/`report` → 渲染 `BrowserPreview`（现有逻辑）
   - 其他 → 渲染 `TestingPanel`

**兼容性**：现有 `BrowserPreview` 逻辑不变，仅在 `panel_mode` 为测试模式时切换。

---

## 4. 非功能需求

| 需求 | 说明 |
|------|------|
| 错误处理 | 所有 API 调用有 try-catch，失败时显示 toast 通知 |
| 加载状态 | 文件上传/解析期间显示 loading 状态 |
| 类型安全 | 所有组件 Props 有完整 TypeScript 类型 |
| 无障碍 | 按钮有 aria-label，表格有 role 属性 |
| 响应式 | 适配现有三列布局，右侧面板 min-width: 400px |

---

## 5. 不在范围内（Phase 3）

- ExecutionDashboard（Phase 8）
- TestReport（Phase 8）
- SSE 实时进度（Phase 4）
- 人工覆盖按钮（Phase 5）
- 趋势图（Phase 8）
