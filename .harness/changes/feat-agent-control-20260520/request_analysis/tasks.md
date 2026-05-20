# 任务拆分清单

## Task 1: 创建 AgentControlBar 组件

- **目标**: 创建独立的 Agent 控制栏组件
- **范围**: 新建 `frontend/src/components/chat/AgentControlBar.tsx`
- **输入**: `sessionId: string` prop
- **输出**: React 组件
- **验收标准**:
  - [ ] 组件正确接收 sessionId prop
  - [ ] 状态为 null 时不渲染任何内容
  - [ ] 正确显示运行中/已暂停/已停止三种状态
  - [ ] 暂停按钮在 running 状态可见，点击调用 pauseAgent
  - [ ] 恢复按钮在 paused 状态可见，点击调用 resumeAgent
  - [ ] 停止按钮在 running 或 paused 状态可见，点击调用 stopAgent
  - [ ] 每秒轮询 getAgentStatus 更新状态
- **依赖**: 无
- **优先级**: P0

## Task 2: 集成到页面

- **目标**: 将 AgentControlBar 集成到主页面
- **范围**: 修改 `frontend/src/app/page.tsx`
- **输入**: 现有页面结构
- **输出**: 更新后的页面
- **验收标准**:
  - [ ] AgentControlBar 位于 ChatWindow 上方
  - [ ] 正确传递 sessionId 给 AgentControlBar
- **依赖**: Task 1
- **优先级**: P0

## Task 3: 创建变更摘要

- **目标**: 生成变更摘要文档
- **范围**: 创建 summary.md
- **输入**: 阶段产出物
- **输出**: summary.md
- **验收标准**:
  - [ ] 包含需求概述
  - [ ] 包含任务列表
  - [ ] 包含变更文件列表
- **依赖**: Task 1, Task 2
- **优先级**: P1