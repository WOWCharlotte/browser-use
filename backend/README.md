# Browser Use Backend

### Overview

Browser Use Backend is a FastAPI-based backend service that provides AI browser automation capabilities. It integrates with the [browser-use](https://github.com/browser-use/browser-use) library to enable AI agents to autonomously navigate web pages, interact with elements, and complete complex tasks.

### Features

- **Session Management**: Create, read, update, delete conversation sessions
- **Agent Control**: Pause, resume, and stop AI agents
- **AG-UI Protocol**: Standard HTTP agent endpoint with SSE streaming support
- **Browser Automation**: Chrome DevTools Protocol integration
- **SQLite Database**: Lightweight persistent storage for sessions and messages

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

#### Agent Control API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/pause` | Pause agent execution |
| POST | `/api/agent/resume` | Resume paused agent |
| POST | `/api/agent/stop` | Stop agent execution |
| GET | `/api/agent/status/{session_id}` | Get agent status |

#### AG-UI Protocol API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agui` | Run agent with AG-UI protocol (SSE streaming) |

### Project Structure

```
backend/
├── app/
│   ├── __init__.py          # FastAPI app factory
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── api/
│   │   ├── __init__.py     # Router aggregation
│   │   ├── sessions.py     # Session CRUD endpoints
│   │   ├── agent.py        # Agent control endpoints
│   │   └── agui.py         # AG-UI protocol endpoint
│   ├── services/
│   │   ├── session_service.py   # Session business logic
│   │   ├── agent_service.py     # Agent orchestration
│   │   └── browser_service.py   # Browser session management
│   ├── models/
│   │   ├── session.py       # Session data model
│   │   └── message.py       # Message data model
│   ├── db/
│   │   └── database.py      # Database initialization
│   └── utils.py             # Utility functions
├── tests/                   # Test files
├── pyproject.toml           # Project configuration
└── .env                     # Environment variables
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