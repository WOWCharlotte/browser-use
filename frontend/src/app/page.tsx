"use client";

import { useState } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { BrowserPreview } from "@/components/browser/BrowserPreview";
import { Sidebar } from "@/components/sidebar/Sidebar";

export default function Home() {
	const [browserState, setBrowserState] = useState({ url: "", title: "", screenshot: undefined as string | undefined });
	const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

	const handleSessionChange = (sessionId: string) => {
		setCurrentSessionId(sessionId);
	};

	return (
		<div className="grid grid-cols-[240px_440px_1fr] h-dvh">
			<Sidebar currentSessionId={currentSessionId} onSessionChange={handleSessionChange} />
			<div className="h-full border-r border-gray-200">
				<ChatWindow sessionId={currentSessionId || undefined} />
			</div>
			<BrowserPreview state={browserState} />
		</div>
	);
}