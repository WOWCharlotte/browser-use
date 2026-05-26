# Browser Use 后端

### 概述

Browser Use 后端是一个基于 FastAPI 的后端服务，提供 AI 浏览器自动化和自动化测试能力。它集成 [browser-use](https://github.com/browser-use/browser-use) 库，使 AI 智能体能够自主导航网页、交互元素并完成复杂任务。

### 功能特性

- **会话管理**：创建、读取、更新、删除会话
- **智能体控制**：暂停、恢复、停止 AI 智能体
- **AG-UI 协议**：标准 HTTP 智能体端点，支持 SSE 流式输出
- **浏览器自动化**：Chrome DevTools Protocol 集成
- **自动化测试**：
  - 测试计划 CRUD，支持从 Excel/Markdown 文件批量导入
  - 测试用例管理，支持变量集和步骤级配置
  - 测试执行引擎，支持并发控制
  - 测试结果评估（AI 驱动的通过/失败判定）
  - 测试回放录制与播放
  - 测试报告生成
- **SQLite 数据库**：轻量级持久化存储

### 技术栈

- **框架**：FastAPI >= 0.115.0
- **服务器**：Uvicorn (ASGI)
- **数据库**：SQLite (via aiosqlite)
- **智能体**：browser-use >= 0.12.0
- **协议**：ag-ui-protocol >= 0.1.18

### 快速开始

#### 环境要求

- Python >= 3.11
- uv 包管理器

#### 安装

```bash
cd backend

# 创建虚拟环境
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# 或：.venv\Scripts\activate  # Windows

# 安装依赖
uv sync
```

#### 配置

复制 `.env.example` 到 `.env` 并配置 LLM 设置：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
LLM_MODEL="qwen-vl-max"
LLM_API_KEY="your-api-key"
LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

#### 运行

```bash
uv run uvicorn app.main:app --reload --port 8888
```

服务将在 `http://localhost:8888` 启动

### API 端点

#### 会话 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/sessions` | 获取所有会话 |
| POST | `/api/sessions` | 创建新会话 |
| GET | `/api/sessions/{session_id}` | 获取会话详情 |
| PUT | `/api/sessions/{session_id}` | 更新会话标题 |
| DELETE | `/api/sessions/{session_id}` | 删除会话 |
| GET | `/api/sessions/{session_id}/messages` | 获取会话消息 |
| GET | `/api/sessions/{session_id}/browser_states` | 获取浏览器状态历史 |

#### 智能体控制 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/agui` | 使用 AG-UI 协议运行智能体（SSE 流式） |
| POST | `/api/agui/resume/{session_id}` | 恢复暂停的智能体（确认/取消） |

#### 测试计划 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/test-plans` | 获取所有测试计划 |
| POST | `/api/test-plans` | 创建测试计划 |
| GET | `/api/test-plans/{plan_id}` | 获取计划详情（含用例） |
| PUT | `/api/test-plans/{plan_id}` | 更新计划元数据 |
| DELETE | `/api/test-plans/{plan_id}` | 删除计划及所有关联数据 |
| PUT | `/api/test-plans/{plan_id}/confirm` | 确认计划（draft -> confirmed） |
| POST | `/api/test-plans/upload` | 上传并解析测试文件（Excel/Markdown） |
| POST | `/api/test-plans/{plan_id}/cases` | 添加测试用例 |
| GET | `/api/test-plans/{plan_id}/runs` | 获取计划的执行历史 |

#### 测试用例 API

| 方法 | 端点 | 描述 |
|------|------|------|
| PUT | `/api/test-cases/{case_id}` | 更新测试用例 |
| DELETE | `/api/test-cases/{case_id}` | 删除测试用例 |
| GET | `/api/test-cases/{case_id}/variables` | 获取变量集 |
| POST | `/api/test-cases/{case_id}/variables/import` | 导入变量集 |
| DELETE | `/api/test-cases/variables/{set_id}` | 删除变量集 |

#### 测试执行 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/test-runs` | 启动测试执行 |
| GET | `/api/test-runs/{run_id}` | 获取执行状态 |
| GET | `/api/test-runs/{run_id}/results` | 获取执行结果 |
| POST | `/api/test-runs/{run_id}/abort` | 中止执行中的测试 |

#### 测试回放 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/test-replays/{result_id}` | 获取结果的回放数据 |

#### 报告 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/reports/{run_id}` | 获取测试执行报告 |

### 项目结构

```
backend/
├── app/
│   ├── __init__.py              # FastAPI 应用工厂与路由注册
│   ├── main.py                  # 应用入口
│   ├── config.py                # 配置管理
│   ├── utils.py                 # 工具函数（uuid7str 等）
│   ├── api/
│   │   ├── sessions.py         # 会话 CRUD 端点
│   │   ├── agui.py             # AG-UI 协议端点
│   │   ├── test_plans.py       # 测试计划与用例端点
│   │   ├── test_runs.py        # 测试执行端点
│   │   ├── test_replays.py     # 测试回放端点
│   │   └── reports.py          # 报告生成端点
│   ├── services/
│   │   ├── session_service.py       # 会话业务逻辑
│   │   ├── test_plan_service.py     # 测试计划 CRUD 逻辑
│   │   ├── test_execution_service.py # 测试执行引擎
│   │   ├── test_evaluation_service.py # AI 驱动的结果评估
│   │   ├── test_case_logger.py      # 用例级日志与截图
│   │   ├── test_replay_service.py   # 回放录制
│   │   ├── ingestion_service.py     # 文件解析（Excel/Markdown）
│   │   ├── document_flattening.py   # 文档预处理
│   │   └── report_service.py        # 报告生成
│   ├── models/
│   │   ├── session.py          # 会话数据模型
│   │   ├── test_plan.py        # 测试计划/用例模型
│   │   ├── test_run.py         # 测试执行模型
│   │   ├── test_replay.py      # 回放数据模型
│   │   ├── evaluation.py       # 评估模型
│   │   └── ingestion.py        # 文件导入 schema
│   └── db/
│       └── database.py         # 数据库初始化与迁移
├── tests/                       # 测试文件
├── pyproject.toml               # 项目配置
└── .env                         # 环境变量
```

### 开发

#### 运行测试

```bash
uv run pytest -vxs tests/
```

#### 类型检查

```bash
uv run pyright
```

#### 代码格式化

```bash
uv run ruff check --fix
uv run ruff format
```

### 许可证

MIT
