# 测试编写模式

## 测试结构

```python
import pytest

class TestClickAction:
    """点击动作测试"""

    @pytest.fixture
    def tools_service(self):
        return ToolsService()

    @pytest.mark.asyncio
    async def test_click_button_success(self, tools_service):
        """测试点击按钮成功"""
        # Given
        params = {"element_id": "btn-123"}

        # When
        result = await tools_service.execute("click", params)

        # Then
        assert result.success is True
```

## 命名规范

```python
def test_[功能]_[场景]_[预期结果]:
    ...
```

## 断言风格

```python
# 清晰描述性断言
assert result.status == "success", "操作应该成功"

# 避免
assert result
```

## 测试分类

### 1. 功能测试
验证核心功能正确性

### 2. 边界测试
- 空值
- 最大值/最小值
- 特殊字符

### 3. 异常测试
- 网络错误
- 超时
- 服务不可用

## pytest 配置

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests/ci"]
```
