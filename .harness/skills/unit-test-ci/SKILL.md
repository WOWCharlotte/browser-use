---
name: unit-test-ci
description: 验证CI流水线的正确性和稳定性。触发场景：阶段8-CI验证。确保质量门禁可程序化验证。
---

# CI流水线验证

## 验证命令

```bash
# 测试执行
uv run pytest -vxs tests/ci

# 类型检查
uv run pyright

# 格式化检查
uv run ruff check --fix
uv run ruff format
```

## 质量门禁（必须同时满足）

```
status == SUCCESS
total_tests > 0      # 禁止tests=0
passed == total
type_check == PASS
format_check == PASS
```

## 验证流程

```
CI执行完成
    ↓
status == SUCCESS?
    ↓ No → 失败
    ↓ Yes
    ↓
total_tests > 0?
    ↓ No → MUST FIX: 测试用例数为0
    ↓ Yes
    ↓
passed == total?
    ↓ No → 失败
    ↓ Yes
    ↓
CI验证通过
```

## 回退处理

| 失败类型 | 回退阶段 | 处理方式 |
|----------|----------|----------|
| tests=0 | 阶段5 | 补充测试用例 |
| 编译错误 | 阶段3 | 修复代码 |
| 类型错误 | 阶段3 | 修复类型提示 |
