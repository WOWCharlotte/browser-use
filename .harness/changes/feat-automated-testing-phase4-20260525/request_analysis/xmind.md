---
title: Phase 4 执行引擎 — 思维导图
change_id: feat-automated-testing-phase4-20260525
phase: 1 - 需求分析
date: 2026-05-25
---

# Phase 4 执行引擎思维导图

```mermaid
mindmap
  root((Phase 4 执行引擎))
    后端核心
      test_execution_service.py
        并发控制
          asyncio.Semaphore
          MAX_CONCURRENCY=5 硬上限
        超时控制
          asyncio.wait_for
          session.close(force=True)
        失败重试
          仅 error 状态重试
          max_retries 配置
        中断恢复
          recover_on_startup
          残留 running 标记 error
        断点续跑
          rerun_failed 参数
          跳过已 passed 用例
        用例执行流程
          快照用例内容
          创建独立 BrowserSession
          构建 task prompt
          Agent.run()
          保存轨迹
          调用评估服务
          关闭浏览器
      test_runs.py API
        POST /api/test-runs 启动
        GET /api/test-runs/{id} 状态
        POST /api/test-runs/{id}/abort 中止
        GET /api/test-runs/{id}/results 结果
        PUT /api/test-results/{id}/override 覆盖
        GET /api/test-results/{id}/screenshot 截图
        GET /api/test-results/{id}/logs 日志
        GET /api/test-results/{id}/logs/stream SSE日志流
        POST /api/test-results/{id}/retry 单条重试
    进度推送
      AG-UI 协议扩展
        StateSnapshot 全量
          执行开始
          执行结束
          页面刷新恢复
        StateDelta 增量
          JSON Patch RFC 6902
          单用例状态变更
      agui.py 扩展
        map STATE_DELTA 事件
        StateDeltaEvent 映射
      事件回调
        on_event 回调模式
        与 agent_service 一致
    前端组件
      useStateSnapshot 扩展
        onStateDeltaEvent 处理
        fast-json-patch 库
      ExecutionDashboard
        ExecutionSummaryBar
          进度条
          通过率
          指标卡
          总计时器
          中止按钮
        CaseList
          原生滚动
          Accordion 展开
          CaseRow 状态标签
        CaseDetail
          LogStream SSE
          CaseScreenshot
          重试按钮
        ExecutionComplete
          汇总结果
          查看报告按钮
    日志系统
      用例执行日志
        独立文件 per case
        TestCaseLogger 封装
        结构化文本 + 时间戳
      系统日志
        RotatingFileHandler
        10MB x 5 files
      SSE 实时日志流
        tail -f 模式
        展开时连接
        收起时断开
```
