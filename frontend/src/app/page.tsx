"use client";

import { useState, useEffect } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { BrowserPreview } from "@/components/browser/BrowserPreview";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { useStateSnapshot } from "@/hooks/useStateSnapshot";

export default function Home() {
	const [browserState, setBrowserState] = useState({ url: "", title: "", screenshot: undefined as string | undefined });
	const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
	const [currentIndex, setCurrentIndex] = useState<number | null>(null);
	const { history } = useStateSnapshot();

	useEffect(() => {
		if (history.length > 0 && currentIndex === null) {
			setCurrentIndex(history.length - 1);
		}
	}, [history, currentIndex]);

	const currentSnapshot = history[currentIndex ?? 0];

	useEffect(() => {
		if (currentSnapshot) {
			setBrowserState({
				url: (currentSnapshot.url as string) || "",
				title: (currentSnapshot.title as string) || "",
				screenshot: (currentSnapshot.screenshot as string | undefined) || undefined,
			});
		}
	}, [currentSnapshot]);

	const handlePrevScreenshot = () => {
		setCurrentIndex((prev) => Math.max((prev ?? 0) - 1, 0));
	};

	const handleNextScreenshot = () => {
		setCurrentIndex((prev) => Math.min((prev ?? 0) + 1, history.length - 1));
	};

	const handleSessionChange = (sessionId: string) => {
		setCurrentSessionId(sessionId);
	};

	return (
		<div className="grid grid-cols-[240px_440px_1fr] h-dvh">
			<Sidebar currentSessionId={currentSessionId} onSessionChange={handleSessionChange} />
			<div className="h-full min-h-0 border-r border-gray-200">
				<ChatWindow sessionId={currentSessionId || undefined} />
			</div>
			<BrowserPreview
				state={browserState}
				currentIndex={currentIndex}
				totalCount={history.length}
				onPrev={handlePrevScreenshot}
				onNext={handleNextScreenshot}
			/>
		</div>
	);
}