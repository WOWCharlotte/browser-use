import { useState, useEffect, useRef } from "react";
import { Message } from "@/types";
import { MessageList } from "./MessageList";
import { InputArea } from "./InputArea";
import { getMessages, streamChat, SSEEvent } from "@/lib/api";

interface Props {
  sessionId: string;
  onEvent: (event: any) => void;
}

export function ChatWindow({ sessionId, onEvent }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const streamCancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    loadMessages();
    return () => {
      if (streamCancelRef.current) {
        streamCancelRef.current();
      }
    };
  }, [sessionId]);

  const loadMessages = async () => {
    try {
      const msgs = await getMessages(sessionId);
      setMessages(msgs);
    } catch (e) {
      console.error("Failed to load messages:", e);
    }
  };

  const handleSend = async (text: string) => {
    // Cancel any existing stream
    if (streamCancelRef.current) {
      streamCancelRef.current();
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      session_id: sessionId,
      role: "user",
      content: text,
      attachments: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);
    onEvent({ type: "user_message", content: text });

    // Start streaming response
    const stream = streamChat({ session_id: sessionId, message: text, attachments: [] }, handleSSEEvent);
    streamCancelRef.current = stream.cancel;
  };

  const handleSSEEvent = (event: SSEEvent) => {
    switch (event.type) {
      case "browser_state":
        onEvent({ type: "browser_state", url: event.url, title: event.title, screenshot: event.screenshot });
        break;
      case "paused":
        setIsTyping(false);
        onEvent({ type: "paused", reason: event.reason });
        break;
      case "done":
        setIsTyping(false);
        onEvent({ type: "done" });
        break;
      case "message":
        if (event.role === "ai") {
          const aiMsg: Message = {
            id: (Date.now() + 1).toString(),
            session_id: sessionId,
            role: "ai",
            content: event.content || "",
            attachments: [],
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, aiMsg]);
        }
        break;
      case "error":
        console.error("Agent error:", event.message);
        setIsTyping(false);
        break;
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-5 min-h-0">
        <MessageList messages={messages} isTyping={isTyping} />
      </div>
      <div className="p-4 border-t border-gray-100 shrink-0">
        <InputArea onSend={handleSend} disabled={isTyping} />
      </div>
    </div>
  );
}