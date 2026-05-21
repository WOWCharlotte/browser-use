# 任务拆分清单

## 任务列表

### Phase 1: 数据模型
- [x] 创建 `TestStepSchema` 模型
- [x] 创建 `TestCaseSchema` 模型
- [x] 创建 `IngestionRequest` 模型
- [x] 创建 `IngestionResponse` 模型
- [x] 添加 Pydantic 验证器

### Phase 2: 文档扁平化
- [x] 创建 `DocumentFlatteningEngine` 类
- [x] 实现 `ExcelFlattener` 子类
- [x] 实现 `MarkdownFlattener` 子类
- [x] 添加文件类型检测

### Phase 3: LLM 解析服务
- [x] 创建 `IngestionService` 类
- [x] 实现占位符校验 `_validate_placeholders`
- [x] 实现变量提取 `_extract_variables_from_text`
- [x] 实现 markdown 解析 `parse_markdown`
- [x] 实现文件解析 `ingest_file`
- [x] 添加重试机制

### Phase 4: API 端点
- [x] 创建 `ingestion` router
- [x] 实现 `POST /ingestion/parse` (统一入口，自动识别文件/内容)

### Phase 5: 测试
- [x] 编写 Pydantic 模型测试
- [x] 编写占位符校验测试
- [x] 编写变量提取测试
- [x] 编写集成测试 (mock LLM)

## 依赖关系
```
models/ingestion.py
    ↓
services/document_flattening.py
    ↓
services/ingestion_service.py
    ↓
api/ingestion.py
```

## 风险评估
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 输出格式不稳定 | 中 | 添加重试机制和校验 |
| Excel 格式多样 | 中 | 扁平化引擎抽象 |