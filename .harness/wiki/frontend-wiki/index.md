# 前端组件 Wiki 总览

## 项目概述

本前端项目是 AI Workspace 的用户界面，基于 Next.js + React + TypeScript 构建。采用 CopilotKit AG-UI 协议与后端通信，实现 AI 驱动的浏览器自动化测试工作台。

## 技术栈

- **框架**: Next.js (App Router)
- **UI**: React 18 + TypeScript
- **AI 通信**: CopilotKit v2 (AG-UI 协议)
- **样式**: Tailwind CSS
- **后端 API**: RESTful + SSE (Server-Sent Events)

## 组件目录结构

```
frontend/src/components/
├── browser/          # 浏览器预览组件
├── chat/             # AI 对话组件
├── sidebar/          # 侧边栏会话管理
└── testing/          # 测试管理组件
```

## 组件文档索引

| 文档 | 说明 |
|------|------|
| [browser.md](./browser.md) | 浏览器预览组件 - 展示 AI 操作的浏览器截图和导航 |
| [chat.md](./chat.md) | AI 对话组件 - 基于 CopilotKit 的聊天窗口 |
| [sidebar.md](./sidebar.md) | 侧边栏组件 - 会话列表管理 |
| [testing.md](./testing.md) | 测试管理组件 - 测试计划编辑、执行监控、报告查看 |

## 数据流架构

```
用户操作 → ChatWindow (CopilotKit AG-UI) → 后端 Agent
                                              ↓
TestingPanel ← SSE/轮询 ← 后端返回测试状态
                                              ↓
BrowserPreview ← 截图数据 ← 浏览器自动化执行
```

## 后端 API 基础地址

所有 API 调用通过环境变量 `NEXT_PUBLIC_API_URL` 配置，默认为 `http://localhost:8888/api`。
