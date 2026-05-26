# Testing 组件

## 组件概述

Testing 组件模块是整个前端最复杂的部分，提供完整的自动化测试管理功能，包括测试计划概览、测试用例编辑、测试执行监控和测试报告查看。它根据后端推送的状态在不同面板模式之间切换。

## 主要子组件

| 组件 | 文件 | 说明 |
|------|------|------|
| TestingPanel | `TestingPanel.tsx` | 顶层路由组件，根据 panel_mode 切换视图 |
| OverviewPanel | `OverviewPanel.tsx` | 测试概览面板，展示计划列表和统计 |
| TestCaseEditor | `TestCaseEditor.tsx` | 测试用例编辑器，支持用例/步骤/变量管理 |
| ExecutionDashboard | `ExecutionDashboard.tsx` | 执行监控面板，实时展示测试进度 |

## 子组件功能说明

### TestingPanel

**功能**: 测试模块的顶层路由组件，根据 `TestingSnapshot.panel_mode` 决定渲染哪个子面板。

**Props**:
- `snapshot: TestingSnapshot | undefined` — 后端推送的测试状态快照
- `sessionId: string | null` — 当前会话 ID
- `browserState: BrowserState` — 浏览器状态（用于 browser 模式）
- 导航回调: `onPrev, onNext, onNavigate, onBack, onForward, onRefresh`
- 测试回调: `onConfirm, onCancel, onPlanUpdate, onViewPlan, onViewRun`

**面板模式切换逻辑**:

| panel_mode | 渲染组件 | 条件 |
|------------|----------|------|
| `case_editor` | TestCaseEditor | 有 test_plan 数据 |
| `execution` | ExecutionDashboard | 有 run_progress + case_statuses |
| `execution`（无数据） | 加载中占位 | 等待数据 |
| `report` | iframe 嵌入报告 | 有 report_url |
| `browser`（默认） | BrowserPreview 或 OverviewPanel | 有截图则显示浏览器，否则显示概览 |

---

### OverviewPanel

**功能**: 测试概览面板，展示所有测试计划的统计信息、最近执行记录和计划列表。

**核心行为**:

1. **统计卡片**: 显示计划总数、通过数、失败数、通过率
2. **最近执行**: 展示最近 8 条执行记录（跨所有计划）
3. **计划列表**: 可展开的计划卡片，显示用例数、状态、最近执行结果
4. **操作**: 查看执行结果/用例详情、删除计划

**子组件**:
- `StatCard` — 统计数字卡片
- `RunRow` — 执行记录行
- `PlanRow` — 计划卡片（可展开）

---

### TestCaseEditor

**功能**: 测试用例编辑器，是最复杂的组件（约 1020 行）。提供完整的测试用例 CRUD、步骤管理、变量集管理功能。

**核心功能模块**:

1. **用例列表管理**:
   - 左侧面板展示所有用例
   - 支持添加/删除用例
   - 校验未通过的用例标红提示

2. **用例元数据编辑**:
   - 用例名称、起始 URL、模块、功能点
   - 防抖自动保存（300ms debounce）

3. **测试步骤管理**:
   - 表格形式编辑步骤
   - 支持拖拽排序
   - 每步包含：操作描述、预期结果、视觉检查点
   - 变量高亮预览（`{varName}` 语法）

4. **变量集管理**:
   - 自动从步骤中提取变量引用
   - 支持手动添加/重命名/删除变量列
   - 变量集行的增删改查
   - 批量保存变量集

5. **确认/取消计划**:
   - 确认前执行全面校验（名称、URL、步骤、变量完整性）
   - 确认后调用 `confirmTestPlan` + `resumeAgentSession`
   - 取消时调用 `resumeAgentSession("cancel")`

**校验规则**:
- 用例名称不能为空
- 起始 URL 必须为合法 http(s) 格式，端口 1-65535
- 至少一个测试步骤
- 步骤操作描述不能为空
- 步骤中引用的变量必须在变量集中定义
- 变量集中不能有空值

**子组件**:
- `CaseDetail` — 用例详情编辑区
- `StepTextarea` — 步骤文本域（带变量高亮预览）

---

### ExecutionDashboard

**功能**: 测试执行实时监控面板，展示整体进度和每个用例的执行状态。

**核心功能模块**:

1. **ExecutionSummaryBar**: 顶部进度条 + 统计（完成数/通过/失败/错误/耗时）+ 中止按钮
2. **CaseRow**: 用例行，显示状态图标、名称、耗时，可展开详情
3. **CaseDetail**: 展开后的用例详情，包含日志/截图标签页和操作按钮
4. **LogStream**: SSE 实时日志流，支持自动滚动和全屏放大
5. **CaseScreenshot**: 截图查看器，支持实时刷新（运行中）和步骤导航（已完成）
6. **ExecutionComplete**: 执行完成后的汇总栏，显示通过率和报告下载链接

**用例状态**:

| 状态 | 图标 | 说明 |
|------|------|------|
| pending | ○ | 等待执行 |
| running | ● (脉冲) | 执行中 |
| paused | ⏸ | 已暂停 |
| passed | ✓ | 通过 |
| failed | ✗ | 失败 |
| error | ⚠ | 错误 |

**操作按钮**:
- 运行中: 暂停、停止
- 已暂停: 恢复、停止
- 失败/错误: 重试
- 已完成: 覆盖（手动修改结果）、重放

## 与后端的交互逻辑

### 相关 API 汇总

#### 测试计划 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/test-plans` | GET | 获取所有测试计划 |
| `/api/test-plans/{id}` | GET | 获取单个计划详情 |
| `/api/test-plans/{id}` | DELETE | 删除测试计划 |
| `/api/test-plans/{id}/confirm` | PUT | 确认测试计划 |
| `/api/test-plans/{id}/cases` | POST | 创建测试用例 |
| `/api/test-plans/{id}/runs` | GET | 获取计划的执行历史 |

#### 测试用例 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/test-cases/{id}` | PUT | 更新测试用例 |
| `/api/test-cases/{id}` | DELETE | 删除测试用例 |
| `/api/test-cases/{id}/variables` | GET | 获取用例变量集 |
| `/api/test-cases/{id}/variables/import` | POST | 批量导入变量集 |
| `/api/test-cases/variables/{id}` | DELETE | 删除单个变量集 |

#### 测试执行 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/test-runs/{id}/abort` | POST | 中止测试运行 |
| `/api/test-runs/{id}/report` | GET | 查看测试报告（HTML） |
| `/api/test-runs/{id}/report/excel` | GET | 下载 Excel 报告 |
| `/api/test-results/{id}/retry` | POST | 重试失败用例 |
| `/api/test-results/{id}/pause` | POST | 暂停执行 |
| `/api/test-results/{id}/resume` | POST | 恢复执行 |
| `/api/test-results/{id}/stop` | POST | 停止执行 |
| `/api/test-results/{id}/override` | PUT | 覆盖测试结果 |
| `/api/test-results/{id}/replay` | POST | 重放测试 |
| `/api/test-results/{id}/screenshot` | GET | 获取实时截图 |
| `/api/test-results/{id}/screenshots` | GET | 获取所有步骤截图 |
| `/api/test-results/{id}/logs/stream` | SSE | 实时日志流 |

#### Agent 会话 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/agui/resume/{sessionId}` | POST | 恢复 Agent 会话（confirm/cancel） |

### 实时通信

#### SSE 日志流

ExecutionDashboard 中的 LogStream 组件通过 EventSource 连接后端日志流：

```
EventSource: GET /api/test-results/{resultId}/logs/stream

事件类型:
- "log": 日志内容（JSON 字符串，可能包含多行）
- "done": 日志流结束
- "error": 连接错误
```

#### 截图轮询

运行中的用例每 3 秒轮询一次实时截图：
```
GET /api/test-results/{resultId}/screenshot
→ { success: true, data: { screenshot: "base64..." } }
```

### 关键交互流程

#### 测试计划确认流程
```
用户点击"确认计划"
    ↓
前端校验所有用例（名称、URL、步骤、变量）
    ↓
PUT /api/test-plans/{id}/confirm — 标记计划为 confirmed
    ↓
POST /api/agui/resume/{sessionId} { action: "confirm" } — 通知 Agent 继续
    ↓
Agent 开始执行测试 → panel_mode 切换为 "execution"
```

#### 测试计划取消流程
```
用户点击"取消" → 确认对话框
    ↓
POST /api/agui/resume/{sessionId} { action: "cancel" } — 通知 Agent 取消
    ↓
Agent 终止 → 返回对话模式
```

#### 用例编辑自动保存
```
用户修改用例字段
    ↓
300ms debounce
    ↓
PUT /api/test-cases/{id} { ...patch }
    ↓
支持 AbortController 取消旧请求
```

#### 执行监控数据流
```
后端通过 TestingSnapshot 推送:
  - run_progress: 整体进度
  - case_statuses: 各用例状态

前端渲染:
  - ExecutionSummaryBar: 进度条 + 统计
  - CaseRow[]: 用例列表
  - LogStream: SSE 实时日志
  - CaseScreenshot: 截图（轮询/一次性加载）
```

### 数据类型

```typescript
// 面板模式
type PanelMode = "browser" | "case_editor" | "execution" | "report";

// 测试快照（后端推送）
interface TestingSnapshot {
  panel_mode: PanelMode;
  test_plan?: TestPlanDetailView;
  run_progress?: RunProgress;
  case_statuses?: CaseStatusEntry[];
  report_url?: string;
}

// 执行进度
interface RunProgress {
  run_id: string;
  total: number;
  completed: number;
  passed: number;
  failed: number;
  error: number;
  started_at: string;
  status: "running" | "completed" | "aborted";
}

// 用例状态条目
interface CaseStatusEntry {
  result_id: string;
  case_id: string;
  case_name: string;
  status: "pending" | "running" | "paused" | "passed" | "failed" | "error";
}
```
