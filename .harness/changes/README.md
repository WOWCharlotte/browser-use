# 变更管理目录

## 目录结构

每个需求在 `.harness/changes/` 下创建独立的变更目录：

```
{变更类型}-{需求名称}-{YYYYMMDD}/
├── summary.md                    # 全流程追溯摘要（一页纸总结）
├── request_analysis/
│   ├── spec.md                   # 需求分析文档
│   ├── tasks.md                  # 任务拆分清单
│   └── review/                   # 需求评审记录
│       ├── spec_review_v1.md
│       ├── spec_review_v2.md
│       ├── tasks_review_v1.md
│       └── tasks_review_v2.md
├── coding/
│   ├── coding_report_v1.md       # 编码报告
│   ├── coding_report_v2.md
│   └── review/
│       └── code_review_v1.md     # 代码评审报告
├── unit_test/
│   ├── test_report_v1.md         # 测试报告
│   ├── test_report_v2.md
│   └── review/
│       └── test_review_v1.md     # 测试评审报告
├── ci_result/
│   └── ci_result_v1.md          # CI 验证结果
└── deployment/
    └── deploy_report_v1.md       # 部署验证报告
```

## 变更类型前缀

| 前缀 | 含义 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| refactor | 重构 |
| docs | 文档更新 |
| test | 测试更新 |
| chore | 杂项 |

## summary.md 格式

```markdown
# 变更摘要

## 基本信息
- 变更ID: {变更类型}-{需求名称}-{YYYYMMDD}
- 创建时间: YYYY-MM-DD HH:mm
- 状态: [进行中/已完成]

## 需求概述
[一句话描述需求]

## 10 阶段执行状态

| 阶段 | 名称 | 状态 | 轮次 | 完成时间 |
|------|------|------|------|----------|
| 1 | 需求分析 | ✅ | - | - |
| 2 | 需求评审 | ⏳ | 1/3 | - |
| ... | ... | ... | ... | ... |

## 评审结论
- 需求评审: 通过 (1 轮)
- 代码评审: 通过 (2 轮)
- 测试评审: 通过 (1 轮)

## 例外情况
[如有，记录]

## 最终交付
- 交付时间: YYYY-MM-DD
- 代码行数: N
- 测试用例数: N
- AI 代码率: XX%
```

## 命名规范

### 目录命名
```
feat-add-user-auth-20260508
fix-price-calculation-20260508
refactor-session-management-20260508
```

### 报告文件命名
```
summary.md
spec_review_v1.md
spec_review_v2.md
coding_report_v1.md
code_review_v1.md
test_report_v1.md
test_review_v1.md
ci_result_v1.md
deploy_report_v1.md
```

## 版本管理策略

- 评审文件采用版本递增策略 (v1, v2, v3...)
- 旧版本永远不删除
- 确保完整的 Audit Trail

## 归档规则

变更完成后：
1. 确认所有阶段完成
2. 确认 summary.md 完整
3. 保留所有版本记录
4. 不删除任何评审轮次文件
