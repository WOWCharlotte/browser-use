---
name: unit-test-write
description: 编写高质量的单元测试。触发场景：阶段5-单元测试编写。遵循改动驱动测试原则，优先使用真实数据。
---

# 单元测试编写

## 核心原则

### 改动驱动测试
改了哪个接口就测哪个接口，而非一刀切测最上层。

### 真实数据优先
优先查询被改动接口的线上真实请求出入参来构造测试数据。

## 测试文件组织

```
tests/
├── ci/
│   ├── test_action_*.py
│   └── conftest.py
└── unit/
```

## 测试流程

1. **识别测试目标**: 回顾代码变更，确定需测试的接口
2. **获取真实数据**: 通过MCP或日志获取真实请求
3. **编写测试用例**: 按规范编写
4. **验证有效性**: 确保测试真正执行代码

## mock规范

| 可以mock | 禁止mock |
|----------|----------|
| LLM调用 | 核心业务逻辑 |
| 外部API | 数据库操作 |

详细测试模板见 [references/test-patterns.md](references/test-patterns.md)

## 质量门禁脚本

阶段完成后，可使用脚本验证产出物：

```bash
python scripts/check_quality_gate.py <change-id>
```

**检查项**:
- test_report_v*.md 存在
- unit_test/review/test_review_v*.md 存在（如有评审）
