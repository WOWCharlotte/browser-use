interface Props {
	url: string;
	onNavigate?: (url: string) => void;
	onBack?: () => void;
	onForward?: () => void;
	onRefresh?: () => void;
}

export function BrowserChrome({ url, onNavigate, onBack, onForward, onRefresh }: Props) {
	return (
		<div className="flex items-center gap-3 px-3 py-2 bg-gray-100 border-b border-b-gray-200">
			<div className="flex gap-1.5">
				<div className="size-2.5 rounded-full bg-red-500" />
				<div className="size-2.5 rounded-full bg-yellow-500" />
				<div className="size-2.5 rounded-full bg-green-500" />
			</div>
			<div className="flex gap-0.5">
				<button
					onClick={onBack}
					className="size-6 rounded hover:bg-gray-200 flex items-center justify-center text-gray-500"
				>
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
						<polyline points="15 18 9 12 15 6" />
					</svg>
				</button>
				<button
					onClick={onForward}
					className="size-6 rounded hover:bg-gray-200 flex items-center justify-center text-gray-500"
				>
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
						<polyline points="9 18 15 12 9 6" />
					</svg>
				</button>
				<button
					onClick={onRefresh}
					className="size-6 rounded hover:bg-gray-200 flex items-center justify-center text-gray-500"
				>
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
						<polyline points="23 4 23 10 17 10" />
						<path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
					</svg>
				</button>
			</div>
			<div className="flex-1 bg-white border border-gray-200 rounded-full px-3 py-1 text-xs text-gray-500 flex items-center gap-1.5">
				<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
					<circle cx="12" cy="12" r="10" />
					<line x1="2" y1="12" x2="22" y2="12" />
				</svg>
				<span className="truncate">{url || "browser — content will appear here"}</span>
			</div>
		</div>
	);
}