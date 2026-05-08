---
name: coding-skill
description: 根据需求规格和设计文档实现高质量代码。触发场景：阶段3-编码实现。包含8分层编码规范和核心约束检查。
---

# 编码实现

## 核心约束（强制执行）

| 约束 | 规则 | 错误示例 |
|------|------|----------|
| 价格字段 | 必须用 `int` 类型（单位：分） | `double price` |
| ID生成 | 使用 `uuid7str` | `uuid.uuid4()` |
| 外部调用 | 必须设置超时 | 无 timeout |
| 错误处理 | 必须 try-catch |裸 raise |

## 8 分层规范

按以下层级顺序实现：Controller → Interface → Service → Domain → Persistence → Adapter → Docs → Test

详细分层规范见 [references/layer-specs.md](references/layer-specs.md)

## 编码检查清单

- [ ] 遵循8分层规范
- [ ] 无硬编码值
- [ ] 错误处理完善
- [ ] 日志使用 `_log_` 前缀
- [ ] 类型提示完整
- [ ] 无 console.log

## 输出文件
- 实现代码
- `.harness/changes/{change-id}/coding/coding_report_v*.md`
