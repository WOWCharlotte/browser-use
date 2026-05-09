import { Message } from "@/types";
import { MessageItem } from "./MessageItem";
import { TypingIndicator } from "./TypingIndicator";

interface Props {
  messages: Message[];
  isTyping: boolean;
}

export function MessageList({ messages, isTyping }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} />
      ))}
      {isTyping && <TypingIndicator />}
    </div>
  );
}