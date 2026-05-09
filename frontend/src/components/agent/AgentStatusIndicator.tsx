import { AgentStatus } from "@/types";

interface Props {
	status: AgentStatus;
}

export function AgentStatusIndicator({ status }: Props) {
	const colors = {
		running: "bg-green-500",
		paused: "bg-yellow-500",
		stopped: "bg-gray-400",
	};

	return (
		<div className="flex items-center gap-2 text-xs">
			<span className={`w-2 h-2 rounded-full ${colors[status]}`} />
			<span className="capitalize">{status}</span>
		</div>
	);
}