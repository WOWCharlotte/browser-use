# Browser 组件

## 组件概述

Browser 组件模块负责在前端展示 AI Agent 操作浏览器时的实时截图和导航状态。它模拟了一个浏览器窗口的外观（地址栏、导航按钮、内容区域），让用户能够直观地观察 AI 的浏览器操作过程。

## 主要子组件

| 组件 | 文件 | 说明 |
|------|------|------|
| BrowserPreview | `BrowserPreview.tsx` | 顶层容器，组合 Chrome 和 Content |
| BrowserChrome | `BrowserChrome.tsx` | 浏览器顶部导航栏（地址栏 + 控制按钮） |
| BrowserContent | `BrowserContent.tsx` | 浏览器内容区域（截图展示） |

## 子组件功能说明

### BrowserPreview

**功能**: 浏览器预览的顶层容器组件，组合了导航栏和内容区域，并支持多截图分页浏览。

**Props**:
- `state: BrowserState` — 当前浏览器状态（URL、标题、截图 base64）
- `currentIndex / totalCount` — 多截图分页索引
- `onPrev / onNext` — 分页切换回调
- `onNavigate / onBack / onForward / onRefresh` — 导航操作回调

**行为**:
- 当 `totalCount > 1` 时显示分页导航条（◀ 1/N ▶）
- 将 URL 传递给 BrowserChrome 显示
- 将截图数据传递给 BrowserContent 渲染

### BrowserChrome

**功能**: 模拟浏览器顶部 Chrome 区域，包含红黄绿三色窗口按钮、前进/后退/刷新导航按钮和地址栏。

**Props**:
- `url: string` — 当前页面 URL
- `onNavigate / onBack / onForward / onRefresh` — 导航操作回调

**行为**:
- 纯展示组件，不直接调用后端 API
- 地址栏显示当前 URL，无 URL 时显示占位文本

### BrowserContent

**功能**: 浏览器内容区域，负责渲染 AI 操作的页面截图。

**Props**:
- `state: BrowserState` — 包含 `screenshot`（base64 PNG）和 `title`

**行为**:
- 有截图时：渲染 `<img>` 标签，src 为 `data:image/png;base64,...`
- 无截图时：显示占位 UI（浏览器图标 + 提示文字）

## 与后端的交互逻辑

Browser 组件本身**不直接调用后端 API**，它是纯展示组件。数据来源于父组件通过以下方式获取：

### 数据获取方式

1. **SSE 流式推送**: 后端通过 `/api/chat` 的 SSE 流推送 `browser_state` 事件，包含 URL、标题和截图
2. **REST 轮询**: 通过 `GET /api/sessions/{sessionId}/browser_states` 获取历史浏览器状态列表

### 相关 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/sessions/{id}/browser_states` | GET | 获取会话的所有浏览器状态快照 |
| `/api/browser/control` | POST | 发送浏览器控制指令（导航、点击等） |

### 数据类型

```typescript
interface BrowserState {
  url: string;       // 当前页面 URL
  title: string;     // 页面标题
  screenshot?: string; // base64 编码的 PNG 截图
}
```

### 数据流

```
后端 Agent 执行浏览器操作
    ↓
截图 + URL + Title 通过 SSE 推送到前端
    ↓
父组件接收并存储 BrowserState
    ↓
BrowserPreview 接收 props 渲染
```
