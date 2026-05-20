# 需求规格说明书

## 1. 概述

为 browser-use 项目的前端实现 Agent 暂停、继续、停止控制功能。用户在聊天界面可以实时控制 Agent 的执行状态。

## 2. 输入

| 参数 | 类型 | 来源 | 描述 |
|------|------|------|------|
| sessionId | string | 用户会话 | 当前会话的唯一标识符 |

## 3. 输出

| 返回值 | 类型 | 格式 | 描述 |
|--------|------|------|------|
| status | "running" \| "paused" \| "stopped" | string | Agent 当前状态 |

## 4. 功能列表

- [ ] 状态显示组件：显示 Agent 当前状态（Running/Paused/Stopped）
- [ ] 暂停按钮：当状态为 Running 时可见，点击调用 pauseAgent API
- [ ] 恢复按钮：当状态为 Paused 时可见，点击调用 resumeAgent API
- [ ] 停止按钮：当状态为 Running 或 Paused 时可见，点击调用 stopAgent API
- [ ] 状态轮询：每秒调用 getAgentStatus 获取最新状态
- [ ] 集成到页面：将控制栏放置在 ChatWindow 上方

## 5. 边界条件

- sessionId 为空时不显示控制栏
- API 调用失败时显示错误状态，不崩溃
- 网络断开时状态显示停止

## 6. 异常处理

| 异常 | 处理方式 |
|------|----------|
| pauseAgent API 失败 | 保持当前状态，控制台报错 |
| resumeAgent API 失败 | 保持当前状态，控制台报错 |
| stopAgent API 失败 | 保持当前状态，控制台报错 |
| getAgentStatus API 失败 | 忽略本次更新，保持上一状态 |
| sessionId 为 null/undefined | 不渲染控制栏 |