# Browser Use 后端

### 概述

Browser Use 后端是一个基于 FastAPI 的后端服务，提供 AI 浏览器自动化能力。它集成 [browser-use](https://github.com/browser-use/browser-use) 库，使 AI 智能体能够自主导航网页、交互元素并完成复杂任务。

### 功能特性

- **会话管理**：创建、读取、更新、删除会话
- **智能体控制**：暂停、恢复、停止 AI 智能体
- **AG-UI 协议**：标准 HTTP 智能体端点，支持 SSE 流式输出
- **浏览器自动化**：Chrome DevTools Protocol 集成
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

#### 智能体控制 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/agent/pause` | 暂停智能体执行 |
| POST | `/api/agent/resume` | 恢复已暂停的智能体 |
| POST | `/api/agent/stop` | 停止智能体执行 |
| GET | `/api/agent/status/{session_id}` | 获取智能体状态 |

#### AG-UI 协议 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/agui` | 使用 AG-UI 协议运行智能体（SSE 流式） |

### 项目结构

```
backend/
├── app/
│   ├── __init__.py          # FastAPI 应用工厂
│   ├── main.py              # 应用入口
│   ├── config.py            # 配置管理
│   ├── api/
│   │   ├── __init__.py      # 路由聚合
│   │   ├── sessions.py      # 会话 CRUD 端点
│   │   ├── agent.py         # 智能体控制端点
│   │   └── agui.py          # AG-UI 协议端点
│   ├── services/
│   │   ├── session_service.py   # 会话业务逻辑
│   │   ├── agent_service.py    # 智能体编排
│   │   └── browser_service.py  # 浏览器会话管理
│   ├── models/
│   │   ├── session.py       # 会话数据模型
│   │   └── message.py       # 消息数据模型
│   ├── db/
│   │   └── database.py      # 数据库初始化
│   └── utils.py             # 工具函数
├── tests/                   # 测试文件
├── pyproject.toml          # 项目配置
└── .env                    # 环境变量
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