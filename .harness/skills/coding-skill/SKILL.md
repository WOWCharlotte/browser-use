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

## 前端编码约束（强制执行）

| 约束 | 规则 | 错误示例 |
|------|------|----------|
| Flex 布局 | 嵌套 flex 子容器必须 `min-h-0` | `flex-1` 无约束导致无限延伸 |
| 防抖回调 | 异步回调使用 ref 持有最新值 | useCallback 闭包捕获过期 state |
| 校验完整性 | 提交前校验所有子项（含空集合） | 只校验非空列表，空列表跳过 |
| 前置条件 | API 调用前校验 sessionId 等上下文 | 空字符串传入导致 500 |
| 缓存新鲜度 | 校验前加载未获取的远程数据 | 用本地缓存 `?? []` 跳过校验 |


## 编码检查清单

- [ ] 遵循8分层规范
- [ ] 无硬编码值
- [ ] 错误处理完善
- [ ] 日志使用 `_log_` 前缀
- [ ] 类型提示完整
- [ ] 无 console.log
- [ ] 前端组件状态隔离正确
- [ ] 表单校验覆盖空集合和子项完整性
- [ ] Flex 布局添加 min-h-0 约束

## 输出文件
- 实现代码
- `.harness/changes/{change-id}/coding/coding_report_v*.md`

## 质量门禁脚本

阶段完成后，可使用脚本验证产出物：

```bash
python scripts/check_quality_gate.py <change-id>
```

**检查项**:
- coding_report_v*.md 存在
- coding/review/code_review_v*.md 存在
