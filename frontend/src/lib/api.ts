import { Session, Message, ChatRequest, BrowserState } from "@/types";
import type { TestPlanDetailView, TestCaseView, VariableSetView } from "@/types/testing";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888/api";

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

export type SSEEventHandler = (event: SSEEvent) => void;

export interface SSEEvent {
	type: "message" | "browser_state" | "done" | "paused" | "error" | "step_start";
	content?: string;
	role?: "ai" | "user";
	url?: string;
	title?: string;
	screenshot?: string;
	reason?: string;
	message?: string;
	step?: number;
}

export function streamChat(
	req: ChatRequest,
	onEvent: SSEEventHandler
): { cancel: () => void } {
	let cancelled = false;

	(async () => {
		try {
			const response = await fetch(`${API_BASE}/chat`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(req),
			});

			if (!response.ok) {
				onEvent({ type: "error", message: `HTTP ${response.status}` });
				return;
			}

			const reader = response.body?.getReader();
			if (!reader) {
				onEvent({ type: "error", message: "No response body" });
				return;
			}

			const decoder = new TextDecoder();
			let buffer = "";

			while (!cancelled) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split("\n");
				buffer = lines.pop() || "";

				for (const line of lines) {
					if (line.startsWith("data: ")) {
						try {
							const data = JSON.parse(line.slice(6));
							onEvent(data);
						} catch (e) {
							// Ignore parse errors for incomplete JSON
						}
					}
				}
			}
		} catch (e) {
			if (!cancelled) {
				onEvent({ type: "error", message: String(e) });
			}
		}
	})();

	return {
		cancel: () => {
			cancelled = true;
		},
	};
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

export async function fetchBrowserStates(sessionId: string): Promise<BrowserState[]> {
	const res = await fetch(`${API_BASE}/sessions/${sessionId}/browser_states`);
	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: "Unknown error" }));
		throw new Error(error.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

// ── Testing API ───────────────────────────────────────────────────────────────

async function _checkOk(res: Response): Promise<unknown> {
	if (!res.ok) {
		const body = await res.json().catch(() => ({ error: "Unknown error" }));
		throw new Error(body.error ?? body.detail ?? body.message ?? `HTTP ${res.status}`);
	}
	// 204 No Content — no body to parse
	if (res.status === 204 || res.headers.get("content-length") === "0") {
		return undefined;
	}
	const body = await res.json();
	return body.data ?? body;
}

export async function fetchTestPlans(): Promise<TestPlanDetailView[]> {
	const res = await fetch(`${API_BASE}/test-plans`);
	return _checkOk(res) as Promise<TestPlanDetailView[]>;
}

export async function getTestPlan(planId: string): Promise<TestPlanDetailView> {
	const res = await fetch(`${API_BASE}/test-plans/${planId}`);
	return _checkOk(res) as Promise<TestPlanDetailView>;
}

export async function uploadTestPlan(
	file: File,
	name: string,
	maxConcurrency = 3,
): Promise<TestPlanDetailView> {
	const form = new FormData();
	form.append("file", file);
	form.append("name", name);
	form.append("max_concurrency", String(maxConcurrency));
	const res = await fetch(`${API_BASE}/test-plans/upload`, { method: "POST", body: form });
	return _checkOk(res) as Promise<TestPlanDetailView>;
}

export async function confirmTestPlan(planId: string): Promise<TestPlanDetailView> {
	const res = await fetch(`${API_BASE}/test-plans/${planId}/confirm`, { method: "PUT" });
	return _checkOk(res) as Promise<TestPlanDetailView>;
}

export async function updateTestCase(
	caseId: string,
	data: Partial<Pick<TestCaseView, "case_name" | "description" | "module" | "function_point" | "start_url" | "steps" | "global_variables">>,
): Promise<TestCaseView> {
	const res = await fetch(`${API_BASE}/test-cases/${caseId}`, {
		method: "PUT",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(data),
	});
	return _checkOk(res) as Promise<TestCaseView>;
}

export async function deleteTestCase(caseId: string): Promise<void> {
	const res = await fetch(`${API_BASE}/test-cases/${caseId}`, { method: "DELETE" });
	if (!res.ok) {
		const body = await res.json().catch(() => ({ error: "Unknown error" }));
		throw new Error(body.error || `HTTP ${res.status}`);
	}
}

export async function getVariableSets(caseId: string): Promise<VariableSetView[]> {
	const res = await fetch(`${API_BASE}/test-cases/${caseId}/variables`);
	return _checkOk(res) as Promise<VariableSetView[]>;
}

export async function importVariableSets(
	caseId: string,
	variableSets: Array<Record<string, string>>,
): Promise<VariableSetView[]> {
	const res = await fetch(`${API_BASE}/test-cases/${caseId}/variables/import`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ variable_sets: variableSets }),
	});
	return _checkOk(res) as Promise<VariableSetView[]>;
}