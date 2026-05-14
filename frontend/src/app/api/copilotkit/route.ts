/**
 * CopilotKit API Route Handler
 *
 * 使用 CopilotKit 运行时端点 + AG-UI HttpAgent 连接后端 browser-use Agent。
 * 参考: showcase/integrations/pydantic-ai/src/app/api/copilotkit/route.ts
 */
import { NextRequest, NextResponse } from "next/server";
import {
	CopilotRuntime,
	ExperimentalEmptyAdapter,
	copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent, AbstractAgent } from "@ag-ui/client";

// 后端 Agent URL - 指向 FastAPI AG-UI 端点
const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8888/api/agui";

console.log("[copilotkit/route] Initializing CopilotKit runtime");
console.log(`[copilotkit/route] AGENT_URL: ${AGENT_URL}`);

/**
 * 创建默认 HttpAgent
 */
function createAgent(): AbstractAgent {
	return new HttpAgent({ url: `${AGENT_URL}` });
}

// 注册 Agent (支持多 Agent 配置)
const agents: Record<string, AbstractAgent> = {
	default: createAgent(),
	agentic_chat: createAgent(),
	human_in_the_loop: createAgent(),
	tool_rendering: createAgent(),
	gen_ui_agent: createAgent(),
	shared_state_read: createAgent(),
	shared_state_write: createAgent(),
	shared_state_streaming: createAgent(),
	prebuilt_sidebar: createAgent(),
	prebuilt_popup: createAgent(),
	chat_slots: createAgent(),
	chat_customization_css: createAgent(),
	headless_simple: createAgent(),
	headless_complete: createAgent(),
	frontend_tools: createAgent(),
	frontend_tools_async: createAgent(),
	readonly_state_agent_context: createAgent(),
	hitl_in_chat: createAgent(),
	hitl_in_app: createAgent(),
};

console.log(
	`[copilotkit/route] Registered ${Object.keys(agents).length} agent names: ${Object.keys(agents).join(", ")}`,
);

export const POST = async (req: NextRequest) => {
	const url = req.url;
	const contentType = req.headers.get("content-type");
	console.log(`[copilotkit/route] POST ${url} (content-type: ${contentType})`);

	try {
		const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
			endpoint: "/api/copilotkit",
			serviceAdapter: new ExperimentalEmptyAdapter(),
			runtime: new CopilotRuntime({
				agents,
				// AG-UI 特定配置
				a2ui: {
					// 自动注入 A2UI 工具 (可选)
					injectA2UITool: false,
				},
			}),
		});

		return await handleRequest(req);
	} catch (error: unknown) {
		const e = error as { message?: string; stack?: string };
		console.error(`[copilotkit/route] Error: ${e.message}`, e.stack);
		return NextResponse.json(
			{ error: e.message, stack: e.stack },
			{ status: 500 },
		);
	}
};

// 处理 CopilotKit 客户端的 GET 请求
export const GET = async (req: NextRequest) => {
	const url = req.nextUrl.pathname;
	console.log(`[copilotkit/route] GET ${url}`);

	// 处理 CopilotKit 线程列表请求
	if (url.endsWith("/threads")) {
		return NextResponse.json({
			threads: [],
			cursor: null,
		});
	}

	// 处理 CopilotKit 运行时信息请求
	if (url.endsWith("/info")) {
		return NextResponse.json({
			agents: Object.keys(agents),
		});
	}

	// 默认返回状态信息
	return NextResponse.json({
		status: "ok",
		service: "copilotkit",
		agentCount: Object.keys(agents).length,
		agents: Object.keys(agents),
	});
};