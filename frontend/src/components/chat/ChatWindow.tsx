/**
 * ChatWindow - AG-UI 协议版本
 *
 * 使用 CopilotKit useAgent hook 替代自定义 SSE 处理。
 */
import { useState, useEffect, useRef } from "react";
import { Message } from "@/types";
import { MessageList } from "./MessageList";
import { InputArea } from "./InputArea";
import { useAgent, useAgentState } from "@copilotkit/react-core";

interface Props {
	sessionId: string;
	onEvent: (event: any) => void;
}

export function ChatWindow({ sessionId, onEvent }: Props) {
	const [messages, setMessages] = useState<Message[]>([]);
	const [isTyping, setIsTyping] = useState(false);
	const streamCancelRef = useRef<(() => void) | null>(null);

	// 使用 CopilotKit useAgent hook
	const { messages: agentMessages, sendMessage, isLoading, setAgentState } = useAgent({
		agent: "default",
	});

	// 同步 CopilotKit messages 到本地状态
	useEffect(() => {
		if (agentMessages && agentMessages.length > 0) {
			const mappedMessages: Message[] = agentMessages.map((msg: any, idx: number) => ({
				id: msg.id || `msg-${idx}`,
				session_id: sessionId,
				role: msg.role as "user" | "ai",
				content: extractContent(msg.content),
				attachments: [],
				created_at: msg.createdAt || new Date().toISOString(),
			}));
			setMessages(mappedMessages);
		}
	}, [agentMessages, sessionId]);

	// 监听 isLoading 状态变化
	useEffect(() => {
		setIsTyping(isLoading);
		if (isLoading) {
			onEvent({ type: "RUN_STARTED" });
		} else {
			onEvent({ type: "RUN_FINISHED" });
		}
	}, [isLoading, onEvent]);

	// 初始加载 (如果需要)
	useEffect(() => {
		// 如果 CopilotKit 没有初始消息，可以从后端加载
		if (!agentMessages || agentMessages.length === 0) {
			// 可选: 加载历史消息
			// loadMessages();
		}
		return () => {
			if (streamCancelRef.current) {
				streamCancelRef.current();
			}
		};
	}, [sessionId]);

	/**
	 * 从消息内容中提取文本
	 */
	function extractContent(content: any): string {
		if (typeof content === "string") {
			return content;
		}
		if (Array.isArray(content)) {
			return content
				.filter((c: any) => c.type === "text")
				.map((c: any) => c.text)
				.join("\n");
		}
		if (content && typeof content === "object") {
			if (content.text) return content.text;
			if (content.content) return extractContent(content.content);
		}
		return "";
	}

	const handleSend = async (text: string) => {
		// 取消任何现有的流
		if (streamCancelRef.current) {
			streamCancelRef.current();
		}

		// 添加用户消息到本地状态
		const userMsg: Message = {
			id: `user-${Date.now()}`,
			session_id: sessionId,
			role: "user",
			content: text,
			attachments: [],
			created_at: new Date().toISOString(),
		};
		setMessages((prev) => [...prev, userMsg]);
		setIsTyping(true);
		onEvent({ type: "user_message", content: text });

		// 使用 CopilotKit sendMessage
		try {
			await sendMessage(text);
		} catch (error: any) {
			console.error("Failed to send message:", error);
			onEvent({ type: "RUN_ERROR", error: error.message });
			setIsTyping(false);
		}
	};

	return (
		<div className="flex flex-col h-full">
			<div className="flex-1 overflow-y-auto p-5 min-h-0">
				<MessageList messages={messages} isTyping={isTyping} />
			</div>
			<div className="p-4 border-t border-gray-100 shrink-0">
				<InputArea onSend={handleSend} disabled={isTyping} />
			</div>
		</div>
	);
}