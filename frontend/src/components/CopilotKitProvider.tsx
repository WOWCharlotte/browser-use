/**
 * CopilotKitProvider 集成
 *
 * 在 Next.js App 根组件中集成 CopilotKitProvider。
 */
"use client";

import { CopilotKit } from "@copilotkit/react-core";

export function CopilotKitProvider({ children }: { children: React.ReactNode }) {
	return (
		<CopilotKit
			runtimeUrl="/api/copilotkit"
			agent="default"
		>
			{children}
		</CopilotKit>
	);
}