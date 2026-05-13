---
name: code-review
description: 进行代码质量和规范的检查。触发场景：阶段7-代码推送。包含PEP8、类型提示、安全性检查。
---

# 代码检查

## 检查项

| 检查项 | 命令 |
|--------|------|
| PEP8规范 | `uv run ruff check --fix` |
| 类型提示 | `uv run pyright` |
| 格式化 | `uv run ruff format` |

## 禁止项

- [ ] console.log 语句
- [ ] 硬编码值
- [ ] 未处理的异常
- [ ] 单字母变量名
- [ ] TODO注释

## 必须项

- [ ] 类型提示
- [ ] 错误处理
- [ ] 日志记录
- [ ] docstring

## 安全检查

- 无硬编码秘钥
- 无SQL注入风险
- 无XSS风险
- 输入验证完善

详细检查清单见 [references/security-checklist.md](references/security-checklist.md)

## 质量门禁脚本

阶段完成后，可使用脚本验证产出物：

```bash
python scripts/check_quality_gate.py <change-id>
```

**检查项**:
- coding/review/code_review_v*.md 存在
- MUST FIX 问题已处理
