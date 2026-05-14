/**
 * ChatWindow - AG-UI CopilotKit 官方预构建组件
 *
 * 使用 CopilotKit v2 官方 CopilotChat 组件，通过 HttpAgent 连接后端 AG-UI 端点。
 * CopilotKit provider 已在 layout.tsx 中全局包裹。
 */
"use client";
import { CopilotChat } from "@copilotkit/react-core/v2";

interface Props {
	sessionId?: string;
	onEvent?: (event: any) => void;
}

export function ChatWindow(_props?: Props) {
	return (
		<div className="flex justify-center items-center h-full w-full">
			<div className="h-full w-full">
				<CopilotChat
					agentId="default"
					className="h-full rounded-none max-w-none mx-0"
				/>
			</div>
		</div>
	);
}