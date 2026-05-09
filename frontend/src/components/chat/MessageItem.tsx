import { Message } from "@/types";

interface Props {
  message: Message;
}

export function MessageItem({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
          isUser
            ? "bg-gradient-to-br from-blue-500 to-blue-700 text-white"
            : "bg-gradient-to-br from-violet-500 to-purple-700 text-white"
        }`}
      >
        {isUser ? "U" : "AI"}
      </div>
      <div
        className={`rounded-lg px-4 py-2 max-w-md ${
          isUser
            ? "bg-blue-50 border border-blue-100"
            : "bg-gray-100 border border-gray-200"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}