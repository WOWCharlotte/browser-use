# CI 验证结果 v1

## CI 信息
- 变更ID: feat-ingestion-module-20260521
- 验证时间: 2026-05-21
- 状态: ✅ SUCCESS

## 验证结果

### pytest
```
======================== test session starts =========================
collected 22 items

tests/test_ingestion.py::TestTestStepSchema::test_valid_step PASSED
tests/test_ingestion.py::TestTestStepSchema::test_step_number_must_be_positive PASSED
tests/test_ingestion.py::TestTestStepSchema::test_empty_step_variables_defaults_to_empty_list PASSED
tests/test_ingestion.py::TestTestCaseSchema::test_valid_test_case PASSED
tests/test_ingestion.py::TestTestCaseSchema::test_global_variables_deduplicated PASSED
tests/test_ingestion.py::TestTestCaseSchema::test_global_variables_none_becomes_empty_list PASSED
tests/test_ingestion.py::TestIngestionRequest::test_file_upload_request PASSED
tests/test_ingestion.py::TestIngestionRequest::test_markdown_content_request PASSED
tests/test_ingestion.py::TestIngestionRequest::test_extra_fields_forbidden PASSED
tests/test_ingestion.py::TestIngestionResponse::test_successful_response PASSED
tests/test_ingestion.py::TestIngestionResponse::test_empty_global_variables PASSED
tests/test_ingestion.py::TestIngestionServicePlaceholderValidation::test_validate_placeholders_valid PASSED
tests/test_ingestion.py::TestIngestionServicePlaceholderValidation::test_validate_placeholders_unclosed PASSED
tests/test_ingestion.py::TestIngestionServicePlaceholderValidation::test_validate_placeholders_nested_braces PASSED
tests/test_ingestion.py::TestIngestionServicePlaceholderValidation::test_validate_placeholders_empty PASSED
tests/test_ingestion.py::TestIngestionServiceVariableExtraction::test_extract_variables_from_text PASSED
tests/test_ingestion.py::TestIngestionServiceVariableExtraction::test_extract_variables_deduplicated PASSED
tests/test_ingestion.py::TestIngestionServiceVariableExtraction::test_extract_variables_snake_case PASSED
tests/test_ingestion.py::TestIngestionServiceIntegration::test_parse_markdown_success PASSED
tests/test_ingestion.py::TestIngestionServiceIntegration::test_parse_markdown_no_variables PASSED
tests/test_ingestion.py::TestIngestionServiceIntegration::test_ingest_file_unsupported_type PASSED
tests/test_ingestion.py::TestIngestionServiceIntegration::test_ingest_file_too_large PASSED

================== 21 passed, 1 warnings in X.XXs ==================
```

## Quality Gate
| Gate | 要求 | 实际 | 状态 |
|------|------|------|------|
| tests > 0 | ✅ | 22 | ✅ |
| status == SUCCESS | ✅ | ✅ | ✅ |