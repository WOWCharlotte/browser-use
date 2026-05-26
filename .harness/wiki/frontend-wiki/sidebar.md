# Sidebar 组件

## 组件概述

Sidebar 组件模块提供会话（Session）管理功能，包括会话列表展示、新建会话、删除会话、重命名会话等操作。它是应用左侧的导航面板，用户通过它在不同的 AI 对话会话之间切换。

## 主要子组件

| 组件 | 文件 | 说明 |
|------|------|------|
| Sidebar | `Sidebar.tsx` | 侧边栏主容器，管理会话列表 |
| ChatHistoryItem | `ChatHistoryItem.tsx` | 单个会话条目，支持编辑和删除 |

## 子组件功能说明

### Sidebar

**功能**: 侧边栏主组件，负责加载和管理所有会话列表，提供新建会话入口。

**Props**:
- `currentSessionId: string | null` — 当前激活的会话 ID
- `onSessionChange: (sessionId: string) => void` — 切换会话的回调

**暴露的 Ref 方法**:
```typescript
interface SidebarHandle {
  refreshSessions: () => Promise<void>;  // 外部触发刷新会话列表
}
```

**核心行为**:

1. **初始加载**: 组件挂载时调用 `fetchSessions()` 加载所有会话
2. **切换刷新**: 当 `currentSessionId` 变化时重新加载列表（捕获后端标题更新）
3. **新建会话**: 调用 `createSession()` 创建新会话，插入列表顶部并切换
4. **删除会话**: 调用 `deleteSession()` 删除，若删除的是当前会话则自动切换到下一个
5. **标题更新**: 通过 `handleTitleChange` 本地更新标题（由子组件触发）
6. **外部刷新**: 通过 `useImperativeHandle` 暴露 `refreshSessions` 方法

### ChatHistoryItem

**功能**: 单个会话条目组件，支持点击切换、双击/按钮编辑标题、删除确认等交互。

**Props**:
- `session: Session` — 会话数据
- `isActive: boolean` — 是否为当前激活会话
- `onClick` — 点击切换回调
- `onDelete` — 删除回调
- `onTitleChange?: (sessionId: string, newTitle: string) => void` — 标题变更回调

**核心行为**:

1. **标题编辑**: 双击或点击编辑按钮进入编辑模式
2. **标题验证**:
   - 不能为空
   - 最大 20 字符
   - 只允许中英文、数字和空格（`/^[a-zA-Z0-9一-龥\s]+$/`）
3. **保存标题**: 调用 `updateSession(id, title)` 持久化到后端
4. **删除确认**: 点击删除按钮弹出确认对话框
5. **错误提示**: 验证失败时弹出错误提示弹窗

## 与后端的交互逻辑

### 相关 API

| API | 方法 | 说明 |
|-----|------|------|
| `/api/sessions` | GET | 获取所有会话列表 |
| `/api/sessions` | POST | 创建新会话 |
| `/api/sessions/{id}` | PUT | 更新会话标题 |
| `/api/sessions/{id}` | DELETE | 删除会话 |

### 数据类型

```typescript
interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}
```

### 交互流程

#### 加载会话列表
```
组件挂载 / sessionId 切换
    ↓
GET /api/sessions → Session[]
    ↓
渲染会话列表
```

#### 新建会话
```
用户点击 "New Chat"
    ↓
POST /api/sessions { title? } → Session
    ↓
插入列表顶部 + 切换到新会话
```

#### 重命名会话
```
用户双击标题 → 进入编辑模式
    ↓
输入新标题 → 前端验证（长度、字符）
    ↓
PUT /api/sessions/{id} { title } → Session
    ↓
更新本地状态
```

#### 删除会话
```
用户点击删除 → 弹出确认对话框
    ↓
确认 → DELETE /api/sessions/{id}
    ↓
从列表移除 + 若为当前会话则切换
```
