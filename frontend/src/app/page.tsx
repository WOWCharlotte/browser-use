"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { BrowserPreview } from "@/components/browser/BrowserPreview";
import { BrowserState, AgentStatus } from "@/types";
import { streamChat, pauseAgent, resumeAgent, stopAgent, getAgentStatus, createSession } from "@/lib/api";

export default function Home() {
  const [currentSessionId, setCurrentSessionId] = useState<string>("");
  const [browserState, setBrowserState] = useState<BrowserState>({ url: "", title: "" });
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("stopped");
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    if (!currentSessionId && !isInitialized) {
      createSession().then((session) => {
        setCurrentSessionId(session.id);
        setIsInitialized(true);
      }).catch((err) => {
        console.error("Failed to create session:", err);
        setIsInitialized(true);
      });
    }
  }, [currentSessionId, isInitialized]);

  const handleEvent = (event: any) => {
    switch (event.type) {
      case "browser_state":
        setBrowserState({ url: event.url, title: event.title, screenshot: event.screenshot });
        break;
      case "paused":
        setAgentStatus("paused");
        break;
      case "done":
        setAgentStatus("stopped");
        break;
      case "user_message":
        setAgentStatus("running");
        break;
    }
  };

  return (
    <div className="grid grid-cols-[240px_440px_1fr] h-screen">
      <Sidebar
        currentSessionId={currentSessionId}
        onSessionChange={setCurrentSessionId}
      />
      <div className="h-full border-r border-gray-200">
        {currentSessionId ? (
          <ChatWindow sessionId={currentSessionId} onEvent={handleEvent} />
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400 h-full">
            Initializing session...
          </div>
        )}
      </div>
      <BrowserPreview state={browserState} />
    </div>
  );
}