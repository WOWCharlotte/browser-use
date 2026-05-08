# AI Workspace GUI Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete AI Workspace GUI Agent with three-column layout (sidebar + chat + real Chrome browser), SSE streaming, CDP integration, and Human-in-the-Loop interruption support.

**Architecture:** Monorepo with two independent repos (frontend + backend). Backend exposes FastAPI endpoints with SSE streaming and CDP browser control. Frontend is Next.js with CopilotKit. Chrome browser embedded via CDP WebSocket.

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, browser-use, aiosqlite, uv
- Frontend: Next.js 14+, TypeScript, Tailwind CSS, CopilotKit, pnpm
- Browser: Chrome with CDP remote debugging

---

## Phase 1: Backend Development

### Task B1: Backend Project Initialization

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: Create project directory structure**

```bash
mkdir -p backend/app/{api,services,models,db}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/services/__init__.py
touch backend/app/models/__init__.py
touch backend/app/db/__init__.py
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "browser-use-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "browser-use@git+https://github.com/browser-use/browser-use",
    "aiosqlite>=0.20.0",
    "pydantic>=2.0.0",
]

[tool.ruff]
indent-style = "tab"
```

- [ ] **Step 3: Create app/config.py**

```python
import os
from pathlib import Path

class Config:
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATABASE_PATH = PROJECT_ROOT / "data" / "ai_workspace.db"
    CHROME_EXECUTABLE_PATH = os.getenv("CHROME_EXECUTABLE_PATH", "")
    CDP_PORT = int(os.getenv("CDP_PORT", "9222"))
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-vl-max")
```

- [ ] **Step 4: Create app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import sessions, chat, browser, agent
from app.db.database import init_db

app = FastAPI(title="AI Workspace Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(browser.router, prefix="/api", tags=["browser"])
app.include_router(agent.router, prefix="/api", tags=["agent"])
```

- [ ] **Step 5: Verify project structure**

Run: `cd backend && uv sync && uv run python -c "from app.main import app; print('OK')"`
Expected: OK

- [ ] **Step 6: Commit**

```bash
cd backend
git init
git add pyproject.toml app/
git commit -m "feat: init backend project structure

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task B2: Database Layer

**Files:**
- Create: `backend/app/db/database.py`
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/message.py`

- [ ] **Step 1: Create database.py**

```python
import aiosqlite
from pathlib import Path
from app.config import Config

DB_PATH = Config.DATABASE_PATH
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS browser_states (
                session_id TEXT PRIMARY KEY,
                url TEXT,
                title TEXT,
                screenshot TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
        """)
        await db.commit()
```

- [ ] **Step 2: Create app/models/session.py**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid_extensions import uuid7str

class Session(BaseModel):
    id: str = Field(default_factory=uuid7str)
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    model_config = ConfigDict(extra="forbid", validate_by_name=True)
```

- [ ] **Step 3: Create app/models/message.py**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from uuid_extensions import uuid7str

class Attachment(BaseModel):
    name: str
    type: str
    data: Optional[str] = None

class Message(BaseModel):
    id: str = Field(default_factory=uuid7str)
    session_id: str
    role: Literal["user", "ai"]
    content: str
    attachments: list[Attachment] = []
    created_at: datetime = Field(default_factory=datetime.now)
    model_config = ConfigDict(extra="forbid", validate_by_name=True)
```

- [ ] **Step 4: Verify database initialization**

Run: `cd backend && uv run python -c "import asyncio; from app.db.database import init_db; asyncio.run(init_db()); print('DB init OK')"`
Expected: DB init OK

- [ ] **Step 5: Commit**

```bash
git add app/db/database.py app/models/session.py app/models/message.py
git commit -m "feat: add SQLite database layer with session/message models

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task B3: Session Service and API

**Files:**
- Create: `backend/app/services/session_service.py`
- Create: `backend/app/api/sessions.py`

- [ ] **Step 1: Create session_service.py**

```python
from typing import Optional
from datetime import datetime
from app.models.session import Session
from app.models.message import Message
from app.db.database import get_db
import aiosqlite

class SessionService:
    async def list_sessions(self) -> list[Session]:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            )
            return [Session(**dict(row)) for row in rows]

    async def get_session(self, session_id: str) -> Optional[Session]:
        async with get_db() as db:
            row = await db.execute_fetchone(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            return Session(**dict(row)) if row else None

    async def create_session(self, title: str = "New conversation") -> Session:
        session = Session(title=title)
        async with get_db() as db:
            await db.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session.id, session.title, session.created_at, session.updated_at)
            )
            await db.commit()
        return session

    async def update_session(self, session_id: str, title: str) -> Optional[Session]:
        async with get_db() as db:
            await db.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, datetime.now(), session_id)
            )
            await db.commit()
        return await self.get_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        async with get_db() as db:
            await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            await db.execute("DELETE FROM browser_states WHERE session_id = ?", (session_id,))
            result = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return result.rowcount > 0

    async def get_messages(self, session_id: str) -> list[Message]:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            )
            return [Message(**dict(row)) for row in rows]

    async def add_message(self, session_id: str, role: str, content: str, attachments: str = None) -> Message:
        from uuid_extensions import uuid7str
        message = Message(id=uuid7str(), session_id=session_id, role=role, content=content, attachments=[])
        if attachments:
            import json
            message.attachments = [Attachment(**a) for a in json.loads(attachments)]
        async with get_db() as db:
            await db.execute(
                "INSERT INTO messages (id, session_id, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (message.id, message.session_id, message.role, message.content, attachments or "[]", message.created_at)
            )
            await db.commit()
        return message
```

- [ ] **Step 2: Create sessions API**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
session_service = SessionService()

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New conversation"

class UpdateSessionRequest(BaseModel):
    title: str

@router.get("/sessions")
async def list_sessions():
    return await session_service.list_sessions()

@router.post("/sessions")
async def create_session(req: CreateSessionRequest):
    return await session_service.create_session(req.title)

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.put("/sessions/{session_id}")
async def update_session(session_id: str, req: UpdateSessionRequest):
    session = await session_service.update_session(session_id, req.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    success = await session_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ok"}

@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    return await session_service.get_messages(session_id)
```

- [ ] **Step 3: Test session API**

Run: `cd backend && uv run uvicorn app.main:app --reload &` then `sleep 3 && curl http://localhost:8000/api/sessions`
Expected: `[]`

- [ ] **Step 4: Commit**

```bash
git add app/services/session_service.py app/api/sessions.py
git commit -m "feat: add session CRUD API endpoints

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task B4: Browser Service (CDP Integration)

**Files:**
- Create: `backend/app/services/browser_service.py`
- Create: `backend/app/api/browser.py`

- [ ] **Step 1: Create browser_service.py**

```python
import asyncio
import json
from typing import Optional
from app.config import Config

class BrowserService:
    def __init__(self):
        self._sessions: dict[str, dict] = {}

    async def create_session(self, session_id: str) -> dict:
        from browser_use.browser.session import BrowserSession
        session = BrowserSession(
            headless=False,
            extra_chromium_args=[f"--remote-debugging-port={Config.CDP_PORT}"]
        )
        await session.start()
        self._sessions[session_id] = {"browser": session, "page": None}
        return await self.get_state(session_id)

    async def get_state(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            return {"url": "", "title": "", "screenshot": ""}
        sess = self._sessions[session_id]
        browser = sess["browser"]
        try:
            page = await browser.get_current_page()
            url = page.url if page else ""
            title = await page.title() if page else ""
            screenshot = await page.screenshot() if page else ""
            return {"url": url, "title": title, "screenshot": screenshot}
        except Exception as e:
            return {"url": "", "title": "", "screenshot": "", "error": str(e)}

    async def execute_action(self, session_id: str, action: str, args: dict) -> dict:
        if session_id not in self._sessions:
            return {"success": False, "error": "Session not found"}
        sess = self._sessions[session_id]
        browser = sess["browser"]
        try:
            page = await browser.get_current_page()
            if action == "navigate":
                await page.goto(args["url"])
            elif action == "click":
                await page.click(args["selector"])
            elif action == "type":
                await page.fill(args["selector"], args["text"])
            elif action == "scroll":
                await page.evaluate(f"window.scrollTo(0, {args.get('y', 0)})")
            elif action == "screenshot":
                pass  # handled in get_state
            return await self.get_state(session_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close_session(self, session_id: str):
        if session_id in self._sessions:
            await self._sessions[session_id]["browser"].stop()
            del self._sessions[session_id]

browser_service = BrowserService()
```

- [ ] **Step 2: Create browser API**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter()

class BrowserControlRequest(BaseModel):
    session_id: str
    action: str
    args: dict[str, Any] = {}

class BrowserControlResponse(BaseModel):
    success: bool
    state: dict

@router.post("/browser/control")
async def control_browser(req: BrowserControlRequest):
    if req.action == "create":
        state = await browser_service.create_session(req.session_id)
        return BrowserControlResponse(success=True, state=state)
    elif req.action == "close":
        await browser_service.close_session(req.session_id)
        return BrowserControlResponse(success=True, state={})
    else:
        state = await browser_service.execute_action(req.session_id, req.action, req.args)
        return BrowserControlResponse(success=("error" not in state), state=state)

@router.get("/browser/state/{session_id}")
async def get_browser_state(session_id: str):
    state = await browser_service.get_state(session_id)
    return state
```

- [ ] **Step 3: Test browser API**

Run: `cd backend && uv run python -c "from app.services.browser_service import browser_service; print('Browser service OK')"`
Expected: Browser service OK

- [ ] **Step 4: Commit**

```bash
git add app/services/browser_service.py app/api/browser.py
git commit -m "feat: add CDP browser service and API

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task B5: Agent Service (browser-use Integration)

**Files:**
- Create: `backend/app/services/agent_service.py`

- [ ] **Step 1: Create agent_service.py**

```python
import asyncio
from typing import Optional, Callable, AsyncGenerator
from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
from app.config import Config
from app.services.browser_service import browser_service

class AgentService:
    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._paused: dict[str, bool] = {}
        self._resume_events: dict[str, asyncio.Event] = {}

    def _create_llm(self):
        return ChatOpenAI(
            model=Config.LLM_MODEL,
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL
        )

    async def create_agent(self, session_id: str, task: str) -> Agent:
        llm = self._create_llm()
        agent = Agent(
            task=task,
            llm=llm,
            use_vision=True,
            max_actions_per_step=1,
        )
        self._agents[session_id] = agent
        self._paused[session_id] = False
        self._resume_events[session_id] = asyncio.Event()
        return agent

    async def run_agent(self, session_id: str, message: str, on_event: Callable) -> AsyncGenerator[dict, None]:
        agent = self._agents.get(session_id)
        if not agent:
            agent = await self.create_agent(session_id, message)
        else:
            agent.task = message

        # Hooks for HITL
        async def on_step_start(agent: Agent):
            if self._paused.get(session_id):
                on_event({"type": "paused", "reason": "awaiting_user"})
                await self._resume_events[session_id].wait()
                self._resume_events[session_id].clear()

        try:
            async for step_result in agent.run(on_step_start=on_step_start):
                if step_result.action:
                    on_event({
                        "type": "action",
                        "tool": step_result.action.name,
                        "args": step_result.action.args
                    })
                if step_result.result:
                    on_event({
                        "type": "message",
                        "content": step_result.result,
                        "role": "ai"
                    })
                state = await browser_service.get_state(session_id)
                on_event({"type": "browser_state", **state})
        except Exception as e:
            on_event({"type": "error", "message": str(e)})
        finally:
            on_event({"type": "done"})

    def pause_agent(self, session_id: str):
        if session_id in self._agents:
            self._paused[session_id] = True
            self._agents[session_id].pause()

    def resume_agent(self, session_id: str):
        if session_id in self._agents and self._paused.get(session_id):
            self._paused[session_id] = False
            self._resume_events[session_id].set()
            self._agents[session_id].resume()

    def stop_agent(self, session_id: str):
        if session_id in self._agents:
            self._agents[session_id].stop()
            self._paused[session_id] = False
            self._resume_events[session_id].set()

    def get_status(self, session_id: str) -> str:
        if session_id not in self._agents:
            return "stopped"
        return "paused" if self._paused.get(session_id) else "running"

agent_service = AgentService()
```

- [ ] **Step 2: Test agent service imports**

Run: `cd backend && uv run python -c "from app.services.agent_service import agent_service; print('Agent service OK')"`
Expected: Agent service OK

- [ ] **Step 3: Commit**

```bash
git add app/services/agent_service.py
git commit -m "feat: add browser-use Agent service with HITL support

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task B6: Chat API (SSE Streaming)

**Files:**
- Create: `backend/app/api/chat.py`
- Create: `backend/app/api/agent.py`

- [ ] **Step 1: Create chat API with SSE**

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.agent_service import agent_service
from app.services.session_service import session_service

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str
    message: str
    attachments: list[dict] = []

async def sse_event(type: str, data: dict):
    yield f"event: {type}\ndata: {json.dumps(data)}\n\n"

@router.post("/chat")
async def chat(req: ChatRequest):
    # Save user message
    await session_service.add_message(req.session_id, "user", req.message)

    async def event_generator():
        async def on_event(event: dict):
            yield f"data: {json.dumps(event)}\n\n"

        try:
            async for event in agent_service.run_agent(req.session_id, req.message, on_event):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: Create agent API for pause/resume/stop**

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class AgentControlRequest(BaseModel):
    session_id: str

@router.post("/agent/pause")
async def pause_agent(req: AgentControlRequest):
    agent_service.pause_agent(req.session_id)
    return {"status": "paused"}

@router.post("/agent/resume")
async def resume_agent(req: AgentControlRequest):
    agent_service.resume_agent(req.session_id)
    return {"status": "running"}

@router.post("/agent/stop")
async def stop_agent(req: AgentControlRequest):
    agent_service.stop_agent(req.session_id)
    return {"status": "stopped"}

@router.get("/agent/status/{session_id}")
async def get_status(session_id: str):
    return {"status": agent_service.get_status(session_id)}
```

- [ ] **Step 3: Add missing import to chat.py**

```python
import json  # add at top
```

- [ ] **Step 4: Test API compilation**

Run: `cd backend && uv run python -c "from app.api.chat import router; from app.api.agent import router; print('API OK')"`
Expected: API OK

- [ ] **Step 5: Commit**

```bash
git add app/api/chat.py app/api/agent.py
git commit -m "feat: add SSE chat API and agent control endpoints

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 2: Frontend Development

### Task F1: Frontend Project Initialization

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`

- [ ] **Step 1: Create Next.js project structure**

```bash
mkdir -p frontend/src/{app,components/{chat,browser,sidebar,agent},hooks,lib,types}
touch frontend/src/app/layout.tsx
touch frontend/src/app/page.tsx
```

- [ ] **Step 2: Create package.json**

```json
{
  "name": "browser-use-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@copilotkit/react": "^1.0.0",
    "@powerhouse-inc/cdp": "^0.1.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Create tailwind.config.ts**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 5: Create next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = nextConfig;
```

- [ ] **Step 6: Create postcss.config.js**

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 7: Install dependencies**

Run: `cd frontend && pnpm install`
Expected: Dependencies installed

- [ ] **Step 8: Commit**

```bash
cd frontend
git init
git add package.json tsconfig.json next.config.js tailwind.config.ts postcss.config.js src/app/
git commit -m "feat: init Next.js frontend project

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task F2: Type Definitions

**Files:**
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: Create type definitions**

```typescript
export type SSEEvent =
  | { type: "message"; content: string; role: "ai" | "user" }
  | { type: "action"; tool: string; args: Record<string, any> }
  | { type: "browser_state"; url: string; title: string; screenshot?: string }
  | { type: "thinking"; content: string }
  | { type: "done" }
  | { type: "paused"; reason: string }
  | { type: "waiting_confirmation"; message: string; options: string[] }
  | { type: "error"; message: string };

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "ai";
  content: string;
  attachments: Attachment[];
  created_at: string;
}

export interface Attachment {
  name: string;
  type: string;
  data?: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
  attachments: Attachment[];
}

export interface BrowserState {
  url: string;
  title: string;
  screenshot?: string;
}

export type AgentStatus = "running" | "paused" | "stopped";
```

- [ ] **Step 2: Commit**

```bash
git add src/types/index.ts
git commit -m "feat: add TypeScript type definitions

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task F3: API Client

**Files:**
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create API client**

```typescript
import { Session, Message, ChatRequest, SSEEvent, BrowserState } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  return res.json();
}

export async function createSession(title?: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function getSession(id: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${id}`);
  return res.json();
}

export async function updateSession(id: string, title: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`${API_BASE}/sessions/${id}`, { method: "DELETE" });
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
  return res.json();
}

export function streamChat(req: ChatRequest): EventSource {
  const params = new URLSearchParams({
    session_id: req.session_id,
    message: req.message,
  });
  return new EventSource(`${API_BASE}/chat?${params}`);
}

export async function controlBrowser(
  sessionId: string,
  action: string,
  args: Record<string, any>
): Promise<{ success: boolean; state: BrowserState }> {
  const res = await fetch(`${API_BASE}/browser/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, action, args }),
  });
  return res.json();
}

export async function pauseAgent(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/agent/pause`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function resumeAgent(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/agent/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function stopAgent(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/agent/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function getAgentStatus(sessionId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/agent/status/${sessionId}`);
  const data = await res.json();
  return data.status;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/lib/api.ts
git commit -m "feat: add API client for backend communication

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task F4: ChatWindow Components

**Files:**
- Create: `frontend/src/components/chat/MessageItem.tsx`
- Create: `frontend/src/components/chat/MessageList.tsx`
- Create: `frontend/src/components/chat/TypingIndicator.tsx`
- Create: `frontend/src/components/chat/ChatWindow.tsx`
- Create: `frontend/src/components/chat/InputArea.tsx`

- [ ] **Step 1: Create MessageItem.tsx**

```tsx
import { Message } from "@/types";

interface Props {
  message: Message;
}

export function MessageItem({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
          isUser
            ? "bg-gradient-to-br from-blue-500 to-blue-700 text-white"
            : "bg-gradient-to-br from-violet-500 to-purple-700 text-white"
        }`}
      >
        {isUser ? "U" : "AI"}
      </div>
      <div
        className={`rounded-lg px-4 py-2 max-w-md ${
          isUser
            ? "bg-blue-50 border border-blue-100"
            : "bg-gray-100 border border-gray-200"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create TypingIndicator.tsx**

```tsx
export function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center">
        <span className="text-white text-xs">AI</span>
      </div>
      <div className="bg-gray-100 border border-gray-200 rounded-lg px-4 py-3">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create MessageList.tsx**

```tsx
import { Message } from "@/types";
import { MessageItem } from "./MessageItem";
import { TypingIndicator } from "./TypingIndicator";

interface Props {
  messages: Message[];
  isTyping: boolean;
}

export function MessageList({ messages, isTyping }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} />
      ))}
      {isTyping && <TypingIndicator />}
    </div>
  );
}
```

- [ ] **Step 4: Create InputArea.tsx**

```tsx
import { useState, useRef, KeyboardEvent } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function InputArea({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text.trim());
      setText("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  return (
    <div className="flex gap-2 items-end">
      <div className="flex-1 flex items-end gap-2 bg-white border border-gray-200 rounded-lg px-4 py-2 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask me anything..."
          disabled={disabled}
          className="flex-1 resize-none border-none outline-none text-sm bg-transparent"
          rows={1}
        />
      </div>
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white disabled:bg-gray-300 hover:bg-blue-600 transition-colors"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>
  );
}
```

- [ ] **Step 5: Create ChatWindow.tsx**

```tsx
import { useState, useEffect } from "react";
import { Message } from "@/types";
import { MessageList } from "./MessageList";
import { InputArea } from "./InputArea";
import { fetchSessions, getMessages } from "@/lib/api";

interface Props {
  sessionId: string;
  onEvent: (event: any) => void;
}

export function ChatWindow({ sessionId, onEvent }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    loadMessages();
  }, [sessionId]);

  const loadMessages = async () => {
    const msgs = await getMessages(sessionId);
    setMessages(msgs);
  };

  const handleSend = async (text: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      session_id: sessionId,
      role: "user",
      content: text,
      attachments: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);
    onEvent({ type: "user_message", content: text });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-5">
        <MessageList messages={messages} isTyping={isTyping} />
      </div>
      <div className="p-4 border-t border-gray-100">
        <InputArea onSend={handleSend} disabled={isTyping} />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add src/components/chat/
git commit -m "feat: add ChatWindow components (MessageList, InputArea, TypingIndicator)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task F5: BrowserPreview Component (CDP Integration)

**Files:**
- Create: `frontend/src/components/browser/BrowserChrome.tsx`
- Create: `frontend/src/components/browser/BrowserContent.tsx`
- Create: `frontend/src/components/browser/BrowserPreview.tsx`

- [ ] **Step 1: Create BrowserChrome.tsx**

```tsx
interface Props {
  url: string;
  onNavigate?: (url: string) => void;
  onBack?: () => void;
  onForward?: () => void;
  onRefresh?: () => void;
}

export function BrowserChrome({ url, onNavigate, onBack, onForward, onRefresh }: Props) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-gray-100 border-b border-gray-200">
      <div className="flex gap-1.5">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
        <div className="w-2.5 h-2.5 rounded-full bg-green-500" />
      </div>
      <div className="flex gap-0.5">
        <button onClick={onBack} className="w-6 h-6 rounded hover:bg-gray-200 flex items-center justify-center text-gray-500">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <button onClick={onForward} className="w-6 h-6 rounded hover:bg-gray-200 flex items-center justify-center text-gray-500">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
        <button onClick={onRefresh} className="w-6 h-6 rounded hover:bg-gray-200 flex items-center justify-center text-gray-500">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </button>
      </div>
      <div className="flex-1 bg-white border border-gray-200 rounded-full px-3 py-1 text-xs text-gray-500 flex items-center gap-1.5">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
        </svg>
        <span className="truncate">{url || "browser — content will appear here"}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create BrowserContent.tsx**

```tsx
import { BrowserState } from "@/types";

interface Props {
  state: BrowserState;
}

export function BrowserContent({ state }: Props) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 bg-gray-50">
      {state.screenshot ? (
        <img
          src={`data:image/png;base64,${state.screenshot}`}
          alt={state.title}
          className="max-w-full max-h-full object-contain"
        />
      ) : (
        <>
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-violet-100 to-purple-100 flex items-center justify-center text-violet-500">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          <p className="text-sm text-gray-400">Browser preview area</p>
          <p className="text-xs text-gray-400 opacity-70">Embedded browser will render content here</p>
          <div className="flex gap-1.5">
            <span className="w-1.5 h-1.5 bg-gray-300 rounded-full" />
            <span className="w-1.5 h-1.5 bg-gray-300 rounded-full" />
            <span className="w-1.5 h-1.5 bg-gray-300 rounded-full" />
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create BrowserPreview.tsx**

```tsx
import { BrowserState } from "@/types";
import { BrowserChrome } from "./BrowserChrome";
import { BrowserContent } from "./BrowserContent";

interface Props {
  state: BrowserState;
  onNavigate?: (url: string) => void;
  onBack?: () => void;
  onForward?: () => void;
  onRefresh?: () => void;
}

export function BrowserPreview({ state, onNavigate, onBack, onForward, onRefresh }: Props) {
  return (
    <div className="flex flex-col h-full bg-white">
      <BrowserChrome
        url={state.url}
        onNavigate={onNavigate}
        onBack={onBack}
        onForward={onForward}
        onRefresh={onRefresh}
      />
      <BrowserContent state={state} />
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add src/components/browser/
git commit -m "feat: add BrowserPreview component with CDP integration

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task F6: Sidebar Component

**Files:**
- Create: `frontend/src/components/sidebar/ChatHistoryItem.tsx`
- Create: `frontend/src/components/sidebar/HistoryList.tsx`
- Create: `frontend/src/components/sidebar/Sidebar.tsx`

- [ ] **Step 1: Create ChatHistoryItem.tsx**

```tsx
import { Session } from "@/types";

interface Props {
  session: Session;
  isActive: boolean;
  onClick: () => void;
  onDelete: () => void;
}

export function ChatHistoryItem({ session, isActive, onClick, onDelete }: Props) {
  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer group ${
        isActive ? "bg-blue-50" : "hover:bg-gray-100"
      }`}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={isActive ? "text-blue-500" : "text-gray-400"}>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
      <span className={`flex-1 text-sm truncate ${isActive ? "text-blue-600 font-medium" : "text-gray-600"}`}>
        {session.title}
      </span>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="opacity-0 group-hover:opacity-100 w-5 h-5 rounded hover:bg-red-100 flex items-center justify-center text-gray-400 hover:text-red-500"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
        </svg>
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create Sidebar.tsx**

```tsx
import { useState, useEffect } from "react";
import { Session } from "@/types";
import { fetchSessions, createSession, deleteSession } from "@/lib/api";
import { ChatHistoryItem } from "./ChatHistoryItem";

interface Props {
  currentSessionId: string | null;
  onSessionChange: (sessionId: string) => void;
}

export function Sidebar({ currentSessionId, onSessionChange }: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    const data = await fetchSessions();
    setSessions(data);
  };

  const handleNewChat = async () => {
    const session = await createSession();
    setSessions((prev) => [session, ...prev]);
    onSessionChange(session.id);
  };

  const handleDelete = async (sessionId: string) => {
    await deleteSession(sessionId);
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    if (currentSessionId === sessionId && sessions.length > 1) {
      onSessionChange(sessions.find((s) => s.id !== sessionId)?.id || "");
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
      <div className="p-3 flex items-center gap-2 border-b border-gray-200">
        <div className="w-7 h-7 bg-blue-500 rounded-lg flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="white" strokeWidth="1.5">
            <path d="M8 2L14 5V11L8 14L2 11V5L8 2Z" />
          </svg>
        </div>
        <span className="font-semibold text-sm">AI Workspace</span>
      </div>
      <button
        onClick={handleNewChat}
        className="mx-3 my-2 flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:border-blue-400 hover:text-blue-500 shadow-sm"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        New Chat
      </button>
      <div className="flex-1 overflow-y-auto px-2 py-1">
        {sessions.map((session) => (
          <ChatHistoryItem
            key={session.id}
            session={session}
            isActive={session.id === currentSessionId}
            onClick={() => onSessionChange(session.id)}
            onDelete={() => handleDelete(session.id)}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/sidebar/
git commit -m "feat: add Sidebar component with chat history

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task F7: Main Page Integration

**Files:**
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/app/page.tsx`

- [ ] **Step 1: Create globals.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 2: Create page.tsx**

```tsx
"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { BrowserPreview } from "@/components/browser/BrowserPreview";
import { BrowserState, AgentStatus } from "@/types";
import { streamChat, pauseAgent, resumeAgent, stopAgent, getAgentStatus, createSession } from "@/lib/api";

export default function Home() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [browserState, setBrowserState] = useState<BrowserState>({ url: "", title: "" });
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("stopped");

  useEffect(() => {
    if (!currentSessionId) {
      createSession().then((session) => {
        setCurrentSessionId(session.id);
      });
    }
  }, []);

  const handleEvent = (event: any) => {
    switch (event.type) {
      case "browser_state":
        setBrowserState({ url: event.url, title: event.title, screenshot: event.screenshot });
        break;
      case "paused":
        setAgentStatus("paused");
        break;
      case "done":
        setAgentStatus("stopped");
        break;
      case "user_message":
        setAgentStatus("running");
        break;
    }
  };

  return (
    <div className="grid grid-cols-[240px_440px_1fr] h-screen">
      <Sidebar
        currentSessionId={currentSessionId}
        onSessionChange={setCurrentSessionId}
      />
      {currentSessionId && (
        <ChatWindow sessionId={currentSessionId} onEvent={handleEvent} />
      )}
      <BrowserPreview state={browserState} />
    </div>
  );
}
```

- [ ] **Step 3: Update layout.tsx**

```tsx
import "./globals.css";

export const metadata = {
  title: "AI Workspace",
  description: "AI Workspace with real Chrome browser",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add src/app/globals.css src/app/page.tsx src/app/layout.tsx
git commit -m "feat: add main page with three-column layout

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 3: Agent Components (HITL)

### Task F8: Agent Components (ConfirmDialog, StatusIndicator)

**Files:**
- Create: `frontend/src/components/agent/ConfirmDialog.tsx`
- Create: `frontend/src/components/agent/AgentStatusIndicator.tsx`

- [ ] **Step 1: Create AgentStatusIndicator.tsx**

```tsx
import { AgentStatus } from "@/types";

interface Props {
  status: AgentStatus;
}

export function AgentStatusIndicator({ status }: Props) {
  const colors = {
    running: "bg-green-500",
    paused: "bg-yellow-500",
    stopped: "bg-gray-400",
  };

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`w-2 h-2 rounded-full ${colors[status]}`} />
      <span className="capitalize">{status}</span>
    </div>
  );
}
```

- [ ] **Step 2: Create ConfirmDialog.tsx**

```tsx
interface Props {
  message: string;
  options: string[];
  onSelect: (option: string) => void;
}

export function ConfirmDialog({ message, options, onSelect }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl p-6 shadow-xl max-w-sm text-center animate-in">
        <div className="w-11 h-11 rounded-full bg-red-100 text-red-500 flex items-center justify-center mx-auto mb-4">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <h3 className="font-semibold text-base mb-2">Confirm Action</h3>
        <p className="text-sm text-gray-500 mb-5">{message}</p>
        <div className="flex gap-2 justify-center">
          {options.map((option) => (
            <button
              key={option}
              onClick={() => onSelect(option)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                option === "confirm"
                  ? "bg-red-500 text-white hover:bg-red-600"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update page.tsx to integrate agent components**

```tsx
// Add to page.tsx imports
import { ConfirmDialog } from "@/components/agent/ConfirmDialog";
import { AgentStatusIndicator } from "@/components/agent/AgentStatusIndicator";

// Add state for confirmation
const [confirmState, setConfirmState] = useState<{
  message: string;
  options: string[];
} | null>(null);

// Add handler for waiting_confirmation events
case "waiting_confirmation":
  setConfirmState({ message: event.message, options: event.options });
  setAgentStatus("paused");
  break;

// Add handler for confirm selection
const handleConfirmSelect = async (option: string) => {
  if (option === "confirm") {
    await resumeAgent(currentSessionId!);
  } else if (option === "skip") {
    // Skip this action
    await resumeAgent(currentSessionId!);
  } else {
    await stopAgent(currentSessionId!);
  }
  setConfirmState(null);
};

// Add to JSX before BrowserPreview
<AgentStatusIndicator status={agentStatus} />
{confirmState && <ConfirmDialog {...confirmState} onSelect={handleConfirmSelect} />}
```

- [ ] **Step 4: Commit**

```bash
git add src/components/agent/
git add src/app/page.tsx
git commit -m "feat: add HITL agent components (ConfirmDialog, AgentStatusIndicator)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 4: Integration

### Task I1: Backend Integration Test

**Files:**
- Test: `backend/tests/test_integration.py`

- [ ] **Step 1: Create integration test**

```python
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health():
    response = client.get("/docs")
    assert response.status_code == 200

def test_session_crud():
    # Create
    response = client.post("/api/sessions", json={"title": "Test"})
    assert response.status_code == 200
    session_id = response.json()["id"]

    # Read
    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200

    # Update
    response = client.put(f"/api/sessions/{session_id}", json={"title": "Updated"})
    assert response.status_code == 200

    # Delete
    response = client.delete(f"/api/sessions/{session_id}")
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/
git commit -m "test: add backend integration tests

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Spec Coverage Checklist

1. **Backend FastAPI** ✅ Task B1-B6
2. **SSE Streaming** ✅ Task B6
3. **SQLite Session Storage** ✅ Task B2-B3
4. **CDP Browser Control** ✅ Task B4
5. **Agent Integration (browser-use)** ✅ Task B5
6. **Agent Pause/Resume/Stop** ✅ Task B5, B6
7. **Frontend Next.js** ✅ Task F1-F8
8. **ChatWindow + InputArea** ✅ Task F4
9. **BrowserPreview with CDP** ✅ Task F5
10. **Sidebar with History** ✅ Task F6
11. **ConfirmDialog (HITL)** ✅ Task F8
12. **AgentStatusIndicator** ✅ Task F8
13. **Three-column Layout** ✅ Task F7
14. **API Client** ✅ Task F3

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-08-ai-workspace-design.md`**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?