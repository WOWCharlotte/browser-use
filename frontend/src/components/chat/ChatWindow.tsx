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
}

export function ChatWindow({ sessionId, onMessageSent }: Props) {
	const [height, setHeight] = useState(0);
	const { agent } = useAgent({ agentId: "default" });
	const msgCountRef = useRef(0);

	useEffect(() => {
		const updateHeight = () => setHeight(window.innerHeight);
		updateHeight();
		window.addEventListener("resize", updateHeight);
		return () => window.removeEventListener("resize", updateHeight);
	}, []);

	useEffect(() => {
		if (!sessionId || !agent) return;

		getMessages(sessionId)
			.then((msgs) => {
				const copilotMsgs = msgs.map((m) => ({
					id: m.id,
					role: ((m.role as string) === "assistant" || (m.role as string) === "ai" ? "assistant" : "user") as "assistant" | "user",
					content: m.content,
				}));
				agent.setMessages(copilotMsgs);
				msgCountRef.current = copilotMsgs.length;
			})
			.catch((err) => {
				console.error("Failed to load historical messages:", err);
			});
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

	return (
		<div style={{ height, overflow: "hidden" }}>
			<CopilotChat
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