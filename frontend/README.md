# browser-use-frontend

[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-cyan)](https://tailwindcss.com/)

AI agent frontend for natural language browser automation, powered by CopilotKit and AG-UI Protocol.

## Features

- Three-panel layout: Sidebar, Chat, Browser Preview
- Real-time browser state snapshots via AG-UI Protocol
- Session-based conversation management
- Natural language browser automation

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
NEXT_PUBLIC_COPILOTKIT_URL=http://localhost:3000
```

## Architecture

```
frontend/src/
├── app/
│   ├── layout.tsx       # Root layout with CopilotKit provider
│   └── page.tsx         # Main three-panel layout
├── components/
│   ├── browser/         # Browser preview components
│   ├── chat/            # Chat interface
│   └── sidebar/         # Session management
├── hooks/
│   └── useStateSnapshot.ts  # Agent state subscription
└── types/
    └── index.ts         # Shared types
```

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **UI**: React 18, TailwindCSS 4
- **Agent UI**: CopilotKit v1.57
- **Protocol**: AG-UI Protocol (`@ag-ui/client`)

## Backend Connection

The frontend connects to a Python backend via:

- **HTTP Agent** (`/api/copilotkit`) - Agent configuration and session management
- **AG-UI SSE** (`/api/ag-ui`) - Streaming agent state snapshots

See `backend/app/api/` for backend implementation.

## License

MIT
