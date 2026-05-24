---
reviewer: expert-reviewer
date: 2026-05-24
verdict: APPROVED (with conditions)
---

# Spec 评审报告

## 总体评价

Phase 2 的核心解析功能（文档解析 + LLM 提取 + 变量合并）已在 Phase 1 中完成（`ingestion_service.py` 已重构）。Phase 2 剩余工作仅为变量集 CSV/Excel 批量导入，范围明确。Phase 3 前端方案整体可行，需补充以下条件后可进入编码。

## 问题清单

### MUST FIX（已在编码前修订）

**[P2-1] 变量集追加 vs 替换语义**
- 决策：文件导入为**追加**（不删除现有变量集），`set_index` 从现有最大值+1 开始
- 理由：用户可能分批导入不同数据集，全量替换会丢失已有数据

**[P2-2] CSV 列名与 global_variables 的校验**
- 决策：**不强制校验**，允许导入任意列名的变量集
- 理由：用户可能先导入变量集再编辑用例步骤，强制校验会阻断工作流

**[P3-1] panel_mode 状态来源**
- 决策：`panel_mode` 来自 `useStateSnapshot` 的 `snapshot.panel_mode`，由后端 Agent 推送
- 当 snapshot 为 undefined 或 panel_mode 为 'browser' 时，显示现有 BrowserPreview

**[P3-2] 失焦保存防抖**
- 决策：300ms 防抖，使用 `useCallback` + `setTimeout`

### SHOULD FIX（已纳入实现）

- `VariableFileParser` 放在 `app/services/variable_file_parser.py`
- 文件大小校验基于原始字节数
- `FileAttachment.tsx` 为通用组件，可复用于 Chat 和 Testing 面板

## 结论

APPROVED。Phase 2 解析功能已完成，仅需实现变量集文件导入。Phase 3 前端方案可行，条件已在上方明确。
