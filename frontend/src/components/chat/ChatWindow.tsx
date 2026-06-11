/**
 * ChatWindow - AG-UI CopilotKit 官方预构建组件
 *
 * 使用 CopilotKit v2 官方 CopilotChat 组件，通过 HttpAgent 连接后端 AG-UI 端点。
 * CopilotKit provider 已在 layout.tsx 中全局包裹。
 */
"use client";
import React, { useState, useEffect, useRef } from "react";
import { CopilotChat } from "@copilotkit/react-core/v2";
import { useAgent } from "@copilotkit/react-core/v2";
import { getMessages } from "@/lib/api";

interface Props {
	sessionId?: string;
	onMessageSent?: () => void;
	onFirstMessage?: () => void;
}

export function ChatWindow({ sessionId, onMessageSent, onFirstMessage }: Props) {
	const [height, setHeight] = useState(0);
	const { agent } = useAgent({ agentId: "default" });
	const msgCountRef = useRef(0);
	const firstMessageFiredRef = useRef(false);

	useEffect(() => {
		const updateHeight = () => setHeight(window.innerHeight);
		updateHeight();
		window.addEventListener("resize", updateHeight);
		return () => window.removeEventListener("resize", updateHeight);
	}, []);

	useEffect(() => {
		if (!agent) return;
		if (!sessionId) {
			agent.setMessages([]);
			msgCountRef.current = 0;
			prevHasUserMsgRef.current = false;
			firstMessageFiredRef.current = false;
			return;
		}

		let cancelled = false;
		getMessages(sessionId)
			.then((msgs) => {
				if (cancelled) return;
				const copilotMsgs = msgs.map((m) => ({
					id: m.id,
					role: ((m.role as string) === "assistant" || (m.role as string) === "ai" ? "assistant" : "user") as "assistant" | "user",
					content: m.content,
				}));
				agent.setMessages(copilotMsgs);
				msgCountRef.current = copilotMsgs.length;
			})
			.catch((err) => {
				if (cancelled) return;
				console.error("Failed to load historical messages:", err);
			});
		return () => {
			cancelled = true;
		};
	}, [sessionId, agent]);

	// Detect new messages via agent subscriber
	useEffect(() => {
		if (!agent || !onMessageSent) return;

		const subscriber = {
			onMessagesChanged({ messages }: { messages: ReadonlyArray<unknown> }) {
				if (messages.length > msgCountRef.current) {
					msgCountRef.current = messages.length;
					onMessageSent();
				}
			},
		};

		const { unsubscribe } = agent.subscribe(subscriber);
		return unsubscribe;
	}, [agent, onMessageSent]);

	// Watch for first user message to notify parent for auto session handling
	const prevHasUserMsgRef = useRef(false);
	useEffect(() => {
		if (!agent) return;

		const hasUserMessage = agent.messages.some(
			(m) => typeof m === "object" && m !== null && "role" in m && (m as { role?: unknown }).role === "user",
		);
		if (hasUserMessage && !prevHasUserMsgRef.current && !firstMessageFiredRef.current && !sessionId) {
			firstMessageFiredRef.current = true;
			onFirstMessage?.();
		}
		prevHasUserMsgRef.current = hasUserMessage;
	}, [agent?.messages, sessionId, onFirstMessage]);

	return (
		<div style={{ height, overflow: "hidden" }}>
			<CopilotChat
				key={sessionId ?? "empty-session"}
				agentId="default"
				threadId={sessionId}
				style={{ height }}
				attachments={{
					enabled: true,
					accept: ".xlsx,.xls,.md,.markdown",
					maxSize: 5 * 1024 * 1024,
				}}
			/>
		</div>
	);
}
