/**
 * CopilotKit Info Endpoint
 *
 * 处理 CopilotKit 客户端的 /api/copilotkit/info 请求。
 */
import { NextRequest, NextResponse } from "next/server";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8888/api/agui";

export const GET = async (req: NextRequest) => {
	console.log(`[copilotkit/info] GET`);

	return NextResponse.json({
		agents: ["default"],
		agentUrl: AGENT_URL,
	});
};
