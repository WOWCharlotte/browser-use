# Browser Use Backend

### Overview

Browser Use Backend is a FastAPI-based backend service that provides AI browser automation and automated testing capabilities. It integrates with the [browser-use](https://github.com/browser-use/browser-use) library to enable AI agents to autonomously navigate web pages, interact with elements, and complete complex tasks.

### Features

- **Session Management**: Create, read, update, delete conversation sessions
- **Agent Control**: Pause, resume, and stop AI agents
- **AG-UI Protocol**: Standard HTTP agent endpoint with SSE streaming support
- **Browser Automation**: Chrome DevTools Protocol integration
- **Automated Testing**:
  - Test plan CRUD with bulk import from Excel/Markdown files
  - Test case management with variable sets and step-level configuration
  - Test execution engine with concurrency control
  - Test result evaluation (AI-powered pass/fail determination)
  - Test replay recording and playback
  - Test reports generation
- **SQLite Database**: Lightweight persistent storage

### Tech Stack

- **Framework**: FastAPI >= 0.115.0
- **Server**: Uvicorn (ASGI)
- **Database**: SQLite (via aiosqlite)
- **Agent**: browser-use >= 0.12.0
- **Protocol**: ag-ui-protocol >= 0.1.18

### Quick Start

#### Prerequisites

- Python >= 3.11
- uv package manager

#### Installation

```bash
cd backend

# Create virtual environment
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
uv sync
```

#### Configuration

Copy `.env.example` to `.env` and configure your LLM settings:

```bash
cp .env.example .env
```

Edit `.env`:

```env
LLM_MODEL="qwen-vl-max"
LLM_API_KEY="your-api-key"
LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

#### Running

```bash
uv run uvicorn app.main:app --reload --port 8888
```

The server will start at `http://localhost:8888`

### API Endpoints

#### Sessions API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sessions` | List all sessions |
| POST | `/api/sessions` | Create a new session |
| GET | `/api/sessions/{session_id}` | Get session details |
| PUT | `/api/sessions/{session_id}` | Update session title |
| DELETE | `/api/sessions/{session_id}` | Delete a session |
| GET | `/api/sessions/{session_id}/messages` | Get session messages |
| GET | `/api/sessions/{session_id}/browser_states` | Get browser state history |

#### Agent Control API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agui` | Run agent with AG-UI protocol (SSE streaming) |
| POST | `/api/agui/resume/{session_id}` | Resume paused agent (confirm/cancel) |

#### Test Plans API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/test-plans` | List all test plans |
| POST | `/api/test-plans` | Create a test plan |
| GET | `/api/test-plans/{plan_id}` | Get plan with cases |
| PUT | `/api/test-plans/{plan_id}` | Update plan metadata |
| DELETE | `/api/test-plans/{plan_id}` | Delete plan and all related data |
| PUT | `/api/test-plans/{plan_id}/confirm` | Confirm plan (draft -> confirmed) |
| POST | `/api/test-plans/upload` | Upload and parse test file (Excel/Markdown) |
| POST | `/api/test-plans/{plan_id}/cases` | Add a test case |
| GET | `/api/test-plans/{plan_id}/runs` | Get run history for a plan |

#### Test Cases API

| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT | `/api/test-cases/{case_id}` | Update a test case |
| DELETE | `/api/test-cases/{case_id}` | Delete a test case |
| GET | `/api/test-cases/{case_id}/variables` | Get variable sets |
| POST | `/api/test-cases/{case_id}/variables/import` | Import variable sets |
| DELETE | `/api/test-cases/variables/{set_id}` | Delete a variable set |

#### Test Runs API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/test-runs` | Start a test run |
| GET | `/api/test-runs/{run_id}` | Get run status |
| GET | `/api/test-runs/{run_id}/results` | Get run results |
| POST | `/api/test-runs/{run_id}/abort` | Abort a running test |

#### Test Replays API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/test-replays/{result_id}` | Get replay data for a result |

#### Reports API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/{run_id}` | Get test run report |

### Project Structure

```
backend/
├── app/
│   ├── __init__.py              # FastAPI app factory & router registration
│   ├── main.py                  # Application entry point
│   ├── config.py                # Configuration management
│   ├── utils.py                 # Utility functions (uuid7str, etc.)
│   ├── api/
│   │   ├── sessions.py         # Session CRUD endpoints
│   │   ├── agui.py             # AG-UI protocol endpoint
│   │   ├── test_plans.py       # Test plan & case endpoints
│   │   ├── test_runs.py        # Test execution endpoints
│   │   ├── test_replays.py     # Test replay endpoints
│   │   └── reports.py          # Report generation endpoints
│   ├── services/
│   │   ├── session_service.py       # Session business logic
│   │   ├── test_plan_service.py     # Test plan CRUD logic
│   │   ├── test_execution_service.py # Test execution engine
│   │   ├── test_evaluation_service.py # AI-powered result evaluation
│   │   ├── test_case_logger.py      # Per-case logging & screenshots
│   │   ├── test_replay_service.py   # Replay recording
│   │   ├── ingestion_service.py     # File parsing (Excel/Markdown)
│   │   ├── document_flattening.py   # Document preprocessing
│   │   └── report_service.py        # Report generation
│   ├── models/
│   │   ├── session.py          # Session data model
│   │   ├── test_plan.py        # Test plan/case models
│   │   ├── test_run.py         # Test run models
│   │   ├── test_replay.py      # Replay data models
│   │   ├── evaluation.py       # Evaluation models
│   │   └── ingestion.py        # File ingestion schemas
│   └── db/
│       └── database.py         # Database initialization & migrations
├── tests/                       # Test files
├── pyproject.toml               # Project configuration
└── .env                         # Environment variables
```

### Development

#### Running Tests

```bash
uv run pytest -vxs tests/
```

#### Type Checking

```bash
uv run pyright
```

#### Code Formatting

```bash
uv run ruff check --fix
uv run ruff format
```

### License

MIT
