# browser-use-frontend

[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-cyan)](https://tailwindcss.com/)

AI agent frontend for natural language browser automation and automated testing, powered by CopilotKit and AG-UI Protocol.

## Features

- Three-panel layout: Sidebar, Chat, Testing/Browser Preview
- Real-time browser state snapshots via AG-UI Protocol
- Session-based conversation management
- Natural language browser automation
- **Automated Testing**:
  - Test plan management (create, edit, confirm, delete)
  - Test case editor with step-level variable highlighting
  - Test execution dashboard with real-time progress
  - Test result overview with pass/fail statistics
  - Test replay viewer for debugging failed cases

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open http://localhost:3000
```

## Build

```bash
npm run build
npm start
```

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8888/api
```

## Architecture

```
frontend/src/
├── app/
│   ├── layout.tsx           # Root layout with CopilotKit provider
│   └── page.tsx             # Main three-panel layout
├── components/
│   ├── browser/             # Browser preview components
│   ├── chat/                # Chat interface (CopilotChat)
│   ├── sidebar/             # Session management sidebar
│   └── testing/             # Automated testing UI
│       ├── TestingPanel.tsx      # Panel router (editor/execution/overview)
│       ├── TestCaseEditor.tsx    # Test case editing with variable support
│       ├── ExecutionDashboard.tsx # Real-time execution progress
│       └── OverviewPanel.tsx     # Test plans & runs overview
├── hooks/
│   └── useStateSnapshot.ts  # Agent state subscription
├── lib/
│   └── api.ts               # REST API client (sessions, testing, agent)
└── types/
    ├── index.ts             # Shared types
    └── testing.ts           # Testing-specific types
```

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **UI**: React 18, TailwindCSS 4
- **Agent UI**: CopilotKit v2
- **Protocol**: AG-UI Protocol (`@ag-ui/client`)

## Backend Connection

The frontend connects to a Python backend via:

- **AG-UI SSE** (`/api/agui`) - Streaming agent state and execution events
- **Sessions API** (`/api/sessions`) - Conversation CRUD
- **Testing API** (`/api/test-plans`, `/api/test-runs`, `/api/test-replays`) - Automated testing management

See `backend/` for backend implementation.

## License

MIT
