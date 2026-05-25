"use client";

import { useState, useEffect, useCallback } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { TestingPanel } from "@/components/testing/TestingPanel";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { useStateSnapshot } from "@/hooks/useStateSnapshot";
import { fetchBrowserStates } from "@/lib/api";
import { BrowserState } from "@/types";
import type { TestingSnapshot } from "@/types/testing";

export default function Home() {
	const [browserState, setBrowserState] = useState({ url: "", title: "", screenshot: undefined as string | undefined });
	const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
	const [currentIndex, setCurrentIndex] = useState<number | null>(null);
	const [combinedHistory, setCombinedHistory] = useState<BrowserState[]>([]);
	const [testingSnapshot, setTestingSnapshot] = useState<TestingSnapshot | undefined>(undefined);
	const { snapshot, history } = useStateSnapshot();

	// 1. Load historical browser states from SQLite when session changes
	useEffect(() => {
		if (!currentSessionId) {
			setCombinedHistory([]);
			setCurrentIndex(null);
			return;
		}

		// Clear instantly on switch to avoid showing flash of previous session
		setCombinedHistory([]);
		setCurrentIndex(null);

		fetchBrowserStates(currentSessionId)
			.then((states) => {
				setCombinedHistory(states);
				if (states.length > 0) {
					setCurrentIndex(states.length - 1);
				}
			})
			.catch((err) => {
				console.error("Failed to load historical browser states:", err);
			});
	}, [currentSessionId]);

	// 2. Merge live snapshots generated during active execution
	useEffect(() => {
		if (history.length === 0) return;

		setCombinedHistory((prev) => {
			const updated = [...prev];
			let changed = false;

			for (const liveItem of history) {
				const liveUrl = (liveItem.url as string) || "";
				const liveTitle = (liveItem.title as string) || "";
				const liveScreenshot = liveItem.screenshot as string | undefined;

				// De-duplicate: check if this snapshot is already in combined history
				const exists = updated.some(
					(item) =>
						item.url === liveUrl &&
						item.title === liveTitle &&
						item.screenshot === liveScreenshot
				);

				if (!exists) {
					updated.push({
						url: liveUrl,
						title: liveTitle,
						screenshot: liveScreenshot,
					});
					changed = true;
				}
			}

			if (changed) {
				setCurrentIndex(updated.length - 1);
				return updated;
			}
			return prev;
		});
	}, [history]);

	const currentSnapshot = combinedHistory[currentIndex ?? 0];

	useEffect(() => {
		if (currentSnapshot) {
			setBrowserState({
				url: currentSnapshot.url || "",
				title: currentSnapshot.title || "",
				screenshot: currentSnapshot.screenshot || undefined,
			});
		} else {
			// Clear preview if no snapshots exist
			setBrowserState({
				url: "",
				title: "",
				screenshot: undefined,
			});
		}
	}, [currentSnapshot]);

	const handlePrevScreenshot = () => {
		setCurrentIndex((prev) => Math.max((prev ?? 0) - 1, 0));
	};

	const handleNextScreenshot = () => {
		setCurrentIndex((prev) => Math.min((prev ?? 0) + 1, combinedHistory.length - 1));
	};

	const handleSessionChange = (sessionId: string) => {
		setCurrentSessionId(sessionId);
	};

	// 3. Sync testing snapshot from agent state
	useEffect(() => {
		if (!snapshot) {
			setTestingSnapshot(undefined);
			return;
		}
		const panelMode = snapshot.panel_mode as string | undefined;
		if (panelMode && panelMode !== "browser") {
			setTestingSnapshot(snapshot as unknown as TestingSnapshot);
		} else {
			setTestingSnapshot(undefined);
		}
	}, [snapshot]);

	const handlePlanUpdate = useCallback(
		(plan: NonNullable<TestingSnapshot["test_plan"]>) => {
			setTestingSnapshot((prev) => (prev ? { ...prev, test_plan: plan } : prev));
		},
		[],
	);

	const handleConfirm = useCallback(() => {
		setTestingSnapshot(undefined);
	}, []);

	const handleCancel = useCallback(() => {
		setTestingSnapshot(undefined);
	}, []);

	return (
		<div className="grid grid-cols-[240px_440px_1fr] h-dvh">
			<Sidebar currentSessionId={currentSessionId} onSessionChange={handleSessionChange} />
			<div className="h-full min-h-0 border-r border-gray-200 flex flex-col">
				<ChatWindow sessionId={currentSessionId || undefined} />
			</div>
			<TestingPanel
				snapshot={testingSnapshot}
				sessionId={currentSessionId}
				browserState={browserState}
				currentIndex={currentIndex ?? undefined}
				totalCount={combinedHistory.length}
				onPrev={handlePrevScreenshot}
				onNext={handleNextScreenshot}
				onConfirm={handleConfirm}
				onCancel={handleCancel}
				onPlanUpdate={handlePlanUpdate}
			/>
		</div>
	);
}