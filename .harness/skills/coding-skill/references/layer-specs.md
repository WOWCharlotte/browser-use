# 8 分层编码规范详解

## 1. 表现层 (Controller)
**文件**: `controller.py`
- 参数校验
- 异常处理
- 响应格式化

```python
class AgentController:
    async def execute(self, request: Request) -> Response:
        # 参数校验
        self._validate_request(request)
        # 执行
        result = await self._do_execute(request)
        # 格式化响应
        return Response(success=True, data=result)
```

## 2. 接口定义层 (Interface)
**文件**: `views.py`
- DTO 设计原则
- 请求/响应结构

```python
class AgentView(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_by_name=True)
    id: str = Field(default_factory=uuid7str)
    name: str
```

## 3. 应用层 (Service)
**文件**: `service.py`
- 业务逻辑编排
- 事务边界

```python
class AgentService:
    async def create(self, view: AgentView) -> Agent:
        # 业务规则校验
        self._validate_business_rules(view)
        # 持久化
        return await self.repository.save(view)
```

## 4. 领域层 (Domain)
**文件**: `models.py`
- 实体定义
- 值对象
- 领域事件

## 5. 数据层 (Persistence)
**文件**: `repository.py`
- DDL 设计规范
- Mapper 编写

## 6. 适配层 (Adapter)
**文件**: `adapter.py`
- 外部 RPC 调用
- 超时/降级

```python
result = await external_service.call(
    timeout=5.0,
    fallback=None
)
```

## 7. 文档层 (Docs)
- docstring 规范
- 注释要求

## 8. 测试层 (Test)
- 测试文件组织
- mock 规范

## ID生成规范

```python
from uuid_extensions import uuid7str

id: str = Field(default_factory=uuid7str)
```

## 日志规范

```python
def _log_request(self, request: Request) -> None:
    logger.info(f"Request: {request.action}")
```
