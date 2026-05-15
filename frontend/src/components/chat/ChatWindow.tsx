/**
 * ChatWindow - AG-UI CopilotKit 官方预构建组件
 *
 * 使用 CopilotKit v2 官方 CopilotChat 组件，通过 HttpAgent 连接后端 AG-UI 端点。
 * CopilotKit provider 已在 layout.tsx 中全局包裹。
 */
"use client";
import React, { useState, useEffect } from "react";
import { CopilotChat } from "@copilotkit/react-core/v2";

interface Props {
	sessionId?: string;
}

export function ChatWindow({ sessionId }: Props) {
	const [height, setHeight] = useState(0);

	useEffect(() => {
		const updateHeight = () => setHeight(window.innerHeight);
		updateHeight();
		window.addEventListener("resize", updateHeight);
		return () => window.removeEventListener("resize", updateHeight);
	}, []);

	return (
		<div style={{ height, overflow: "hidden" }}>
			<CopilotChat agentId="default" threadId={sessionId} style={{ height }} />
		</div>
	);
}