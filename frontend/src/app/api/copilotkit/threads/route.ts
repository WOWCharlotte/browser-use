/**
 * CopilotKit Threads Endpoint
 *
 * 处理 CopilotKit 客户端的 /api/copilotkit/threads 请求。
 */
import { NextRequest, NextResponse } from "next/server";

export const GET = async (req: NextRequest) => {
	const { searchParams } = req.nextUrl;
	const agentId = searchParams.get("agentId") || "default";

	console.log(`[copilotkit/threads] GET agentId=${agentId}`);

	// 返回空线程列表
	return NextResponse.json({
		threads: [],
		cursor: null,
	});
};
