import { BrowserState } from "@/types";
import { BrowserChrome } from "./BrowserChrome";
import { BrowserContent } from "./BrowserContent";

interface Props {
	state: BrowserState;
	currentIndex?: number;
	totalCount?: number;
	onPrev?: () => void;
	onNext?: () => void;
	onNavigate?: (url: string) => void;
	onBack?: () => void;
	onForward?: () => void;
	onRefresh?: () => void;
}

export function BrowserPreview({ state, currentIndex = 0, totalCount = 1, onPrev, onNext, onNavigate, onBack, onForward, onRefresh }: Props) {
	const canGoPrev = currentIndex > 0;
	const canGoNext = currentIndex < totalCount - 1;

	return (
		<div className="flex flex-col h-full bg-white">
			<BrowserChrome
				url={state.url}
				onNavigate={onNavigate}
				onBack={onBack}
				onForward={onForward}
				onRefresh={onRefresh}
			/>
			{totalCount > 1 && (
				<div className="flex items-center justify-center gap-4 py-2 border-b border-gray-100">
					<button
						type="button"
						onClick={onPrev}
						disabled={!canGoPrev}
						className="px-3 py-1 text-sm rounded-md transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
					>
						◀
					</button>
					<span className="text-xs text-gray-500">
						{currentIndex + 1} / {totalCount}
					</span>
					<button
						type="button"
						onClick={onNext}
						disabled={!canGoNext}
						className="px-3 py-1 text-sm rounded-md transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
					>
						▶
					</button>
				</div>
			)}
			<BrowserContent state={state} />
		</div>
	);
}