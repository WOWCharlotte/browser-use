---
name: expert-reviewer
description: 从架构、性能、安全角度进行深度评审。触发场景：阶段2/4/6-评审。包含Plan Review和Execution Review两种类型。
---

# 专家评审

## 评审类型

| 类型 | 时机 | 内容 | 产出物 |
|------|------|------|--------|
| Plan Review | 阶段2 | spec.md + tasks.md | `*_review_v*.md` |
| Execution Review | 阶段4/6 | 代码/测试 | `*_review_v*.md` |

## 评审检查项

### Plan Review
1. **完整性**: 输入输出是否完整
2. **一致性**: tasks与spec是否匹配
3. **可执行性**: 任务是否可执行
4. **验收标准**: 是否清晰可验证

### Execution Review
1. **正确性**: 逻辑是否正确
2. **规范性**: 是否遵循编码规范
3. **安全性**: 是否有安全漏洞
4. **性能**: 是否有性能问题

## 评审意见格式

```markdown
## 评审意见

### MUST FIX
| 位置 | 问题 | 修改建议 |
|------|------|----------|

### LOW
| 位置 | 问题 | 修改建议 |
|------|------|----------|
```

## 优先级定义

| 优先级 | 含义 | 处理 |
|--------|------|------|
| MUST FIX | 阻塞问题 | 修复前不能进入下一阶段 |
| LOW | 建议改进 | 尽量修复 |
| INFO | 参考信息 | 可选 |

## 质量门禁

- MUST FIX 问题数 = 0
- 评审轮次 ≤ 限制（需求3轮，编码/测试2轮）

详细评审清单见 [references/review-checklist.md](references/review-checklist.md)
