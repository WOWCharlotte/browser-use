# browser-use-frontend

[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-cyan)](https://tailwindcss.com/)

基于 CopilotKit 和 AG-UI Protocol 的 AI 智能体前端，实现自然语言浏览器自动化与自动化测试。

## 功能特性

- 三栏布局：侧边栏、聊天、测试/浏览器预览
- 通过 AG-UI Protocol 实时同步浏览器状态快照
- 基于会话的对话管理
- 自然语言浏览器自动化控制
- **自动化测试**：
  - 测试计划管理（创建、编辑、确认、删除）
  - 测试用例编辑器，支持步骤级变量高亮
  - 测试执行仪表盘，实时展示执行进度
  - 测试结果概览，通过率统计
  - 测试回放查看器，用于调试失败用例

## 快速启动

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

## 构建生产版本

```bash
npm run build
npm start
```

## 环境变量

```env
NEXT_PUBLIC_API_URL=http://localhost:8888/api
```

## 项目结构

```
frontend/src/
├── app/
│   ├── layout.tsx           # 根布局，包含 CopilotKit provider
│   └── page.tsx             # 三栏主布局
├── components/
│   ├── browser/             # 浏览器预览组件
│   ├── chat/                # 聊天界面（CopilotChat）
│   ├── sidebar/             # 侧边栏会话管理
│   └── testing/             # 自动化测试 UI
│       ├── TestingPanel.tsx      # 面板路由（编辑器/执行/概览）
│       ├── TestCaseEditor.tsx    # 测试用例编辑，支持变量
│       ├── ExecutionDashboard.tsx # 实时执行进度仪表盘
│       └── OverviewPanel.tsx     # 测试计划与执行概览
├── hooks/
│   └── useStateSnapshot.ts  # 智能体状态快照订阅
├── lib/
│   └── api.ts               # REST API 客户端（会话、测试、智能体）
└── types/
    ├── index.ts             # 共享类型定义
    └── testing.ts           # 测试相关类型定义
```

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI**: React 18, TailwindCSS 4
- **Agent UI**: CopilotKit v2
- **协议**: AG-UI Protocol (`@ag-ui/client`)

## 后端连接

前端通过以下端点连接 Python 后端：

- **AG-UI SSE** (`/api/agui`) - 流式传输智能体状态和执行事件
- **会话 API** (`/api/sessions`) - 会话 CRUD
- **测试 API** (`/api/test-plans`, `/api/test-runs`, `/api/test-replays`) - 自动化测试管理

后端实现参见 `backend/` 目录。

## License

MIT
