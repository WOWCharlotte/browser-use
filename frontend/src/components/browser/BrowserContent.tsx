import { BrowserState } from "@/types";

interface Props {
	state: BrowserState;
}

export function BrowserContent({ state }: Props) {
	return (
		<div className="flex-1 flex flex-col items-center justify-center gap-4 bg-gray-50">
			{state.screenshot ? (
				<img
					src={`data:image/png;base64,${state.screenshot}`}
					alt={state.title}
					className="max-w-full max-h-full object-contain"
				/>
			) : (
				<>
					<div className="w-14 h-14 rounded-xl bg-linear-to-br from-violet-100 to-purple-100 flex items-center justify-center text-violet-500">
						<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
							<rect x="2" y="3" width="20" height="14" rx="2" />
							<line x1="8" y1="21" x2="16" y2="21" />
							<line x1="12" y1="17" x2="12" y2="21" />
						</svg>
					</div>
					<p className="text-sm text-gray-400">Browser preview area</p>
					<p className="text-xs text-gray-400 opacity-70">Embedded browser will render content here</p>
					<div className="flex gap-1.5">
						<span className="size-1.5 bg-gray-300 rounded-full" />
						<span className="size-1.5 bg-gray-300 rounded-full" />
						<span className="size-1.5 bg-gray-300 rounded-full" />
					</div>
				</>
			)}
		</div>
	);
}