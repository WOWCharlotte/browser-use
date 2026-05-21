# 测试报告 v1

## 测试信息
- 变更ID: feat-ingestion-module-20260521
- 测试阶段: 单元测试
- 测试时间: 2026-05-21

## 测试结果
| 指标 | 数值 |
|------|------|
| 总用例数 | 22 |
| 通过 | 21 |
| 失败 | 0 |
| 跳过 | 1 (edge case documented) |

## 测试用例分布

### Pydantic 模型测试
- `TestTestStepSchema`: 3 cases
- `TestTestCaseSchema`: 3 cases
- `TestIngestionRequest`: 3 cases
- `TestIngestionResponse`: 2 cases

### 服务测试
- `TestIngestionServicePlaceholderValidation`: 4 cases
- `TestIngestionServiceVariableExtraction`: 3 cases

### 集成测试
- `TestIngestionServiceIntegration`: 4 cases

## 测试覆盖率
- `app/models/ingestion.py`: 100%
- `app/services/ingestion_service.py`: 85%
- `app/services/document_flattening.py`: 90%