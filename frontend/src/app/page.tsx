"use client";

import { ChatWindow } from "@/components/chat/ChatWindow";
import { BrowserPreview } from "@/components/browser/BrowserPreview";
import { useState } from "react";

export default function Home() {
	const [browserState, setBrowserState] = useState({ url: "", title: "", screenshot: undefined as string | undefined });

	return (
		<div className="grid grid-cols-[240px_440px_1fr] h-dvh">
			{/* Sidebar */}
			<div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
				<div className="p-3 flex items-center gap-2 border-b border-gray-200">
					<div className="w-7 h-7 bg-blue-500 rounded-lg flex items-center justify-center">
						<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="white" strokeWidth="1.5">
							<path d="M8 2L14 5V11L8 14L2 11V5L8 2Z"></path>
						</svg>
					</div>
					<span className="font-semibold text-sm">AI Workspace</span>
				</div>
				<button className="mx-3 my-2 flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:border-blue-400 hover:text-blue-500 shadow-sm">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
						<line x1="12" y1="5" x2="12" y2="19"></line>
						<line x1="5" y1="12" x2="19" y2="12"></line>
					</svg>
					New Chat
				</button>
				<div className="flex-1 overflow-y-auto px-2 py-1"></div>
			</div>
			{/* Chat Window */}
			<div className="h-full border-r border-gray-200">
				<ChatWindow />
			</div>
			{/* Browser Preview */}
			<BrowserPreview state={browserState} />
		</div>
	);
}