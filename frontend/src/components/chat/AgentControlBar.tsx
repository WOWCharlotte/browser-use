"use client";

import { useState, useEffect } from "react";
import { pauseAgent, resumeAgent, stopAgent, getAgentStatus } from "@/lib/api";
import { AgentStatus } from "@/types";

interface Props {
	sessionId: string;
}

export function AgentControlBar({ sessionId }: Props) {
	const [status, setStatus] = useState<AgentStatus | null>(null);
	const [loading, setLoading] = useState(false);

	useEffect(() => {
		if (!sessionId) {
			setStatus(null);
			return;
		}

		const pollStatus = async () => {
			try {
				const s = await getAgentStatus(sessionId);
				setStatus(s as AgentStatus);
			} catch {
				// ignore errors, keep last status
			}
		};

		pollStatus();
		const interval = setInterval(pollStatus, 1000);
		return () => clearInterval(interval);
	}, [sessionId]);

	const handlePause = async () => {
		setLoading(true);
		try {
			await pauseAgent(sessionId);
			setStatus("paused");
		} catch (e) {
			console.error("Failed to pause agent:", e);
		} finally {
			setLoading(false);
		}
	};

	const handleResume = async () => {
		setLoading(true);
		try {
			await resumeAgent(sessionId);
			setStatus("running");
		} catch (e) {
			console.error("Failed to resume agent:", e);
		} finally {
			setLoading(false);
		}
	};

	const handleStop = async () => {
		setLoading(true);
		try {
			await stopAgent(sessionId);
			setStatus("stopped");
		} catch (e) {
			console.error("Failed to stop agent:", e);
		} finally {
			setLoading(false);
		}
	};

	if (!sessionId) {
		return null;
	}

	const statusColors: Record<AgentStatus, string> = {
		running: "bg-green-500",
		paused: "bg-yellow-500",
		stopped: "bg-red-500",
	};

	const statusLabels: Record<AgentStatus, string> = {
		running: "Running",
		paused: "Paused",
		stopped: "Stopped",
	};

	return (
		<div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
			<div className="flex items-center gap-2">
				{status && (
					<>
						<span
							className={`w-2.5 h-2.5 rounded-full ${statusColors[status]}`}
						/>
						<span className="text-sm font-medium text-gray-700">
							{statusLabels[status]}
						</span>
					</>
				)}
				{!status && (
					<span className="text-sm text-gray-400">Initializing...</span>
				)}
			</div>
			<div className="flex items-center gap-2">
				{status === "running" && (
					<button
						onClick={handlePause}
						disabled={loading}
						className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50"
					>
						Pause
					</button>
				)}
				{status === "paused" && (
					<button
						onClick={handleResume}
						disabled={loading}
						className="px-3 py-1.5 text-sm font-medium text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
					>
						Resume
					</button>
				)}
				{(status === "running" || status === "paused") && (
					<button
						onClick={handleStop}
						disabled={loading}
						className="px-3 py-1.5 text-sm font-medium text-white bg-red-500 rounded-md hover:bg-red-600 disabled:opacity-50"
					>
						Stop
					</button>
				)}
			</div>
		</div>
	);
}