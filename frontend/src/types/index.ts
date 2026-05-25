export type SSEEvent =
  | { type: "message"; content: string; role: "ai" | "user" }
  | { type: "action"; tool: string; args: Record<string, unknown> }
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