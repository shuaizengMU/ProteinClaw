import ReactMarkdown from "react-markdown";
import type { Message } from "../types";
import { ToolCallCard } from "./ToolCallCard";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const calls = message.toolCalls?.filter((e) => e.type === "tool_call") ?? [];
  const obs = message.toolCalls?.filter((e) => e.type === "observation") ?? [];

  return (
    <div className={`message-bubble message-bubble--${message.role}`}>
      <div className="message-role">
        {message.role === "user" ? "You" : "ProteinClaw"}
      </div>

      {calls.map((tc, j) => (
        <ToolCallCard key={j} toolCall={tc} observation={obs[j]} />
      ))}

      {message.role === "assistant" ? (
        <div className="message-content message-content--markdown">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      ) : (
        <div className="message-content">{message.content}</div>
      )}
    </div>
  );
}
