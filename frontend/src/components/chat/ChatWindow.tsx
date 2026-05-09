import { useState, useEffect } from "react";
import { Message } from "@/types";
import { MessageList } from "./MessageList";
import { InputArea } from "./InputArea";
import { getMessages } from "@/lib/api";

interface Props {
  sessionId: string;
  onEvent: (event: any) => void;
}

export function ChatWindow({ sessionId, onEvent }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    loadMessages();
  }, [sessionId]);

  const loadMessages = async () => {
    const msgs = await getMessages(sessionId);
    setMessages(msgs);
  };

  const handleSend = async (text: string) => {
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
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-5">
        <MessageList messages={messages} isTyping={isTyping} />
      </div>
      <div className="p-4 border-t border-gray-100">
        <InputArea onSend={handleSend} disabled={isTyping} />
      </div>
    </div>
  );
}