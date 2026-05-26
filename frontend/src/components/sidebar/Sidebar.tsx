import { useState, useEffect, useRef, useCallback, useImperativeHandle, forwardRef } from "react";
import { Session } from "@/types";
import { fetchSessions, createSession, deleteSession } from "@/lib/api";
import { ChatHistoryItem } from "./ChatHistoryItem";

export interface SidebarHandle {
	refreshSessions: () => Promise<void>;
}

interface Props {
	currentSessionId: string | null;
	onSessionChange: (sessionId: string) => void;
}

export const Sidebar = forwardRef<SidebarHandle, Props>(function Sidebar({ currentSessionId, onSessionChange }, ref) {
	const [sessions, setSessions] = useState<Session[]>([]);
	const prevSessionId = useRef<string | null>(null);

	const loadSessions = useCallback(async () => {
		const data = await fetchSessions();
		setSessions(data);
	}, []);

	useImperativeHandle(ref, () => ({ refreshSessions: loadSessions }), [loadSessions]);

	useEffect(() => {
		loadSessions();
	}, [loadSessions]);

	// Re-fetch when switching sessions (catches backend title updates from previous session)
	useEffect(() => {
		if (currentSessionId && prevSessionId.current && currentSessionId !== prevSessionId.current) {
			loadSessions();
		}
		prevSessionId.current = currentSessionId;
	}, [currentSessionId, loadSessions]);

	const handleNewChat = async () => {
		const session = await createSession();
		setSessions((prev) => [session, ...prev]);
		onSessionChange(session.id);
	};

	const handleDelete = async (sessionId: string) => {
		try {
			await deleteSession(sessionId);
			setSessions((prev) => {
				const remaining = prev.filter((s) => s.id !== sessionId);
				// If we deleted the active session, switch to another
				if (currentSessionId === sessionId) {
					const next = remaining[0]?.id || "";
					// Use setTimeout to avoid setState during render
					setTimeout(() => onSessionChange(next), 0);
				}
				return remaining;
			});
		} catch (e) {
			console.error("Failed to delete session:", e);
		}
	};

	const handleTitleChange = (sessionId: string, newTitle: string) => {
		setSessions((prev) =>
			prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s))
		);
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
						onTitleChange={handleTitleChange}
					/>
				))}
			</div>
		</div>
	);
});