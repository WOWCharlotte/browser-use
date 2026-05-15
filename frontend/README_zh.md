# browser-use-frontend

[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-cyan)](https://tailwindcss.com/)

基于 CopilotKit 和 AG-UI Protocol 的 AI 智能体前端，实现自然语言浏览器自动化。

## 功能特性

- 三栏布局：侧边栏、聊天、浏览器预览
- 通过 AG-UI Protocol 实时同步浏览器状态快照
- 基于会话的对话管理
- 自然语言浏览器自动化控制

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
NEXT_PUBLIC_COPILOTKIT_URL=http://localhost:3000
```

## 项目结构

```
frontend/src/
├── app/
│   ├── layout.tsx       # 根布局，包含 CopilotKit provider
│   └── page.tsx         # 三栏主布局
├── components/
│   ├── browser/         # 浏览器预览组件
│   ├── chat/            # 聊天界面组件
│   └── sidebar/         # 侧边栏会话管理
├── hooks/
│   └── useStateSnapshot.ts  # 智能体状态快照订阅
└── types/
    └── index.ts         # 共享类型定义
```

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI**: React 18, TailwindCSS 4
- **Agent UI**: CopilotKit v1.57
- **协议**: AG-UI Protocol (`@ag-ui/client`)

## 后端连接

前端通过以下端点连接 Python 后端：

- **HTTP Agent** (`/api/copilotkit`) - 智能体配置和会话管理
- **AG-UI SSE** (`/api/ag-ui`) - 流式传输智能体状态快照

后端实现参见 `backend/app/api/`。

## License

MIT
