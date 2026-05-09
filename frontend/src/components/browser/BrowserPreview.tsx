import { BrowserState } from "@/types";
import { BrowserChrome } from "./BrowserChrome";
import { BrowserContent } from "./BrowserContent";

interface Props {
	state: BrowserState;
	onNavigate?: (url: string) => void;
	onBack?: () => void;
	onForward?: () => void;
	onRefresh?: () => void;
}

export function BrowserPreview({ state, onNavigate, onBack, onForward, onRefresh }: Props) {
	return (
		<div className="flex flex-col h-full bg-white">
			<BrowserChrome
				url={state.url}
				onNavigate={onNavigate}
				onBack={onBack}
				onForward={onForward}
				onRefresh={onRefresh}
			/>
			<BrowserContent state={state} />
		</div>
	);
}