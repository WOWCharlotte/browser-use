import { Session, Message, ChatRequest, BrowserState } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function fetchSessions(): Promise<Session[]> {
	const res = await fetch(`${API_BASE}/sessions`);
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

export async function createSession(title?: string): Promise<Session> {
	const res = await fetch(`${API_BASE}/sessions`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ title }),
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

export async function getSession(id: string): Promise<Session> {
	const res = await fetch(`${API_BASE}/sessions/${id}`);
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

export async function updateSession(id: string, title: string): Promise<Session> {
	const res = await fetch(`${API_BASE}/sessions/${id}`, {
		method: "PUT",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ title }),
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

export async function deleteSession(id: string): Promise<void> {
	const res = await fetch(`${API_BASE}/sessions/${id}`, { method: "DELETE" });
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
}

export async function getMessages(sessionId: string): Promise<Message[]> {
	const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

// Note: EventSource does not support custom error handling.
// The caller should listen for 'error' events on the returned EventSource.
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
	args: Record<string, unknown>
): Promise<{ success: boolean; state: BrowserState }> {
	const res = await fetch(`${API_BASE}/browser/control`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ session_id: sessionId, action, args }),
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

export async function pauseAgent(sessionId: string): Promise<void> {
	const res = await fetch(`${API_BASE}/agent/pause`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ session_id: sessionId }),
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
}

export async function resumeAgent(sessionId: string): Promise<void> {
	const res = await fetch(`${API_BASE}/agent/resume`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ session_id: sessionId }),
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
}

export async function stopAgent(sessionId: string): Promise<void> {
	const res = await fetch(`${API_BASE}/agent/stop`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ session_id: sessionId }),
	});
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
}

export async function getAgentStatus(sessionId: string): Promise<string> {
	const res = await fetch(`${API_BASE}/agent/status/${sessionId}`);
	if (!res.ok) {
		throw new Error(`HTTP ${res.status}`);
	}
	return (await res.json()).status as string;
}