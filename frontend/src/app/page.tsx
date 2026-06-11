"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { TestingPanel } from "@/components/testing/TestingPanel";
import { Sidebar, SidebarHandle } from "@/components/sidebar/Sidebar";
import { useStateSnapshot } from "@/hooks/useStateSnapshot";
import { fetchBrowserStates, fetchSessions } from "@/lib/api";
import { BrowserState } from "@/types";
import type { TestingSnapshot } from "@/types/testing";

export default function Home() {
	const [browserState, setBrowserState] = useState({ url: "", title: "", screenshot: undefined as string | undefined });
	const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
	const [currentIndex, setCurrentIndex] = useState<number | null>(null);
	const [combinedHistory, setCombinedHistory] = useState<BrowserState[]>([]);
	const [testingSnapshot, setTestingSnapshot] = useState<TestingSnapshot | undefined>(undefined);
	const { snapshot, history } = useStateSnapshot();
	const sidebarRef = useRef<SidebarHandle>(null);

	// Refresh sidebar sessions when agent history changes (backend may have updated title)
	const prevHistoryLen = useRef(0);
	useEffect(() => {
		if (history.length > prevHistoryLen.current && prevHistoryLen.current > 0) {
			// Delay slightly to let backend commit the title update
			const timer = setTimeout(() => {
				sidebarRef.current?.refreshSessions();
			}, 1000);
			prevHistoryLen.current = history.length;
			return () => clearTimeout(timer);
		}
		prevHistoryLen.current = history.length;
	}, [history.length]);

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

	const handleSessionChange = useCallback((sessionId: string) => {
		setTestingSnapshot(undefined);
		setCurrentSessionId(sessionId);
	}, []);

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

	const handleViewPlan = useCallback(
		(plan: NonNullable<TestingSnapshot["test_plan"]>) => {
			setTestingSnapshot({ panel_mode: "case_editor", test_plan: plan });
		},
		[],
	);

	const handleViewRun = useCallback(async (runId: string) => {
		const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888/api";
		try {
			const [runRes, resultsRes] = await Promise.all([
				fetch(`${API_BASE}/test-runs/${runId}`),
				fetch(`${API_BASE}/test-runs/${runId}/results`),
			]);
			const runData = await runRes.json();
			const resultsData = await resultsRes.json();
			if (!runData.success || !resultsData.success) return;

			const run = runData.data;
			const results = resultsData.data as Array<{ id: string; case_id: string; status: string; case_snapshot_json?: string }>;

			const runProgress = {
				run_id: run.id,
				total: run.total_cases || 0,
				completed: (run.passed_cases || 0) + (run.failed_cases || 0) + (run.error_cases || 0),
				passed: run.passed_cases || 0,
				failed: run.failed_cases || 0,
				error: run.error_cases || 0,
				started_at: run.started_at || new Date().toISOString(),
				status: run.status as "running" | "completed" | "aborted",
			};

			const caseStatuses = results.map((r) => {
				let caseName = r.case_id;
				if (r.case_snapshot_json) {
					try {
						const snap = JSON.parse(r.case_snapshot_json);
						caseName = snap.case_name || caseName;
					} catch { /* ignore */ }
				}
				return {
					result_id: r.id,
					case_id: r.case_id,
					case_name: caseName,
					status: r.status as "pending" | "running" | "paused" | "passed" | "failed" | "error",
				};
			});

			setTestingSnapshot({
				panel_mode: "execution",
				run_progress: runProgress,
				case_statuses: caseStatuses,
			});
		} catch (e) {
			console.error("Failed to load run:", e);
		}
	}, []);

	const handleMessageSent = useCallback(() => {
		// Delay to let backend commit the title update
		setTimeout(() => {
			sidebarRef.current?.refreshSessions();
		}, 1500);
	}, []);

	const handleFirstMessage = useCallback(() => {
		// After first message, wait for backend to create session, then fetch and switch to it
		setTimeout(async () => {
			try {
				const sessions = await fetchSessions();
				if (sessions.length > 0) {
					const latestSession = sessions[0];
					handleSessionChange(latestSession.id);
				}
			} catch (err) {
				console.error("Failed to fetch sessions for auto-switch:", err);
			}
		}, 2000);
	}, [handleSessionChange]);

	return (
		<div className="grid grid-cols-[240px_440px_1fr] h-dvh">
			<Sidebar ref={sidebarRef} currentSessionId={currentSessionId} onSessionChange={handleSessionChange} />
			<div className="h-full min-h-0 border-r border-gray-200 flex flex-col">
				<ChatWindow sessionId={currentSessionId || undefined} onMessageSent={handleMessageSent} onFirstMessage={handleFirstMessage} />
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
				onViewPlan={handleViewPlan}
				onViewRun={handleViewRun}
			/>
		</div>
	);
}
