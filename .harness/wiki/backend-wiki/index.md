# 后端服务 Wiki 总览

本文档为 `backend/app/services/` 目录下所有服务的技术文档索引。

## 服务架构概览

```mermaid
graph TD
    A[前端/API层] --> B[IngestionService]
    A --> C[TestPlanService]
    A --> D[TestExecutionService]
    A --> E[TestReplayService]
    A --> F[ReportService]
    A --> G[SessionService]

    B --> H[DocumentFlatteningEngine]
    B --> I[LLM - ChatOpenAI]
    B --> C

    D --> J[TestCaseLogger]
    D --> K[TestEvaluationService]
    D --> I

    E --> I

    K --> I

    F --> L[Jinja2 Templates]
    F --> M[Playwright PDF]
    F --> N[openpyxl Excel]

    C --> O[(SQLite DB)]
    D --> O
    E --> O
    F --> O
    G --> O
```

## 服务列表

| 服务 | 文件 | 职责 |
|------|------|------|
| [DocumentFlatteningEngine](./document_flattening.md) | `document_flattening.py` | 文档格式转换（Excel/Markdown → 统一Markdown） |
| [IngestionService](./ingestion_service.md) | `ingestion_service.py` | LLM驱动的测试用例智能解析 |
| [TestPlanService](./test_plan_service.md) | `test_plan_service.py` | 测试计划与用例的CRUD管理 |
| [TestExecutionService](./test_execution_service.md) | `test_execution_service.py` | 并行测试执行引擎 |
| [TestEvaluationService](./test_evaluation_service.md) | `test_evaluation_service.py` | LLM驱动的测试结果评估 |
| [TestCaseLogger](./test_case_logger.md) | `test_case_logger.py` | 单用例执行日志记录器 |
| [TestReplayService](./test_replay_service.md) | `test_replay_service.py` | 测试轨迹回放引擎 |
| [ReportService](./report_service.md) | `report_service.py` | 多格式测试报告生成 |
| [SessionService](./session_service.md) | `session_service.py` | 会话与消息管理 |

## 数据流概览

```mermaid
sequenceDiagram
    participant User as 用户
    participant API as API层
    participant Ingest as IngestionService
    participant Plan as TestPlanService
    participant Exec as TestExecutionService
    participant Eval as TestEvaluationService
    participant Report as ReportService

    User->>API: 上传测试文档
    API->>Ingest: ingest_file()
    Ingest->>Ingest: 文档扁平化
    Ingest->>Ingest: LLM解析
    Ingest-->>API: TestPlanParsedSchema

    API->>Plan: import_parsed_plan()
    Plan-->>API: TestPlanDetailView

    User->>API: 启动测试执行
    API->>Exec: start_run()
    Exec->>Exec: 并行执行用例
    Exec->>Eval: evaluate()
    Eval-->>Exec: EvaluationResult
    Exec-->>API: AG-UI事件流

    User->>API: 查看报告
    API->>Report: generate_html/pdf/excel()
    Report-->>API: 报告文件路径
```

## 技术栈

- **运行时**: Python 3.11+ (async)
- **数据库**: SQLite (aiosqlite)
- **LLM**: OpenAI兼容接口 (ChatOpenAI)
- **浏览器自动化**: browser-use (Agent + BrowserSession)
- **报告生成**: Jinja2 (HTML), Playwright (PDF), openpyxl (Excel)
- **文档解析**: pandas (Excel), 原生UTF-8 (Markdown)
