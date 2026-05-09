import { Session } from "@/types";

interface Props {
	session: Session;
	isActive: boolean;
	onClick: () => void;
	onDelete: () => void;
}

export function ChatHistoryItem({ session, isActive, onClick, onDelete }: Props) {
	return (
		<div
			onClick={onClick}
			className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer group ${
				isActive ? "bg-blue-50" : "hover:bg-gray-100"
			}`}
		>
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={isActive ? "text-blue-500" : "text-gray-400"}>
				<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
			</svg>
			<span className={`flex-1 text-sm truncate ${isActive ? "text-blue-600 font-medium" : "text-gray-600"}`}>
				{session.title}
			</span>
			<button
				onClick={(e) => { e.stopPropagation(); onDelete(); }}
				className="opacity-0 group-hover:opacity-100 w-5 h-5 rounded hover:bg-red-100 flex items-center justify-center text-gray-400 hover:text-red-500"
			>
				<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
					<polyline points="3 6 5 6 21 6" />
					<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
				</svg>
			</button>
		</div>
	);
}