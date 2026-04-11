import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Copy, ThumbsUp, ThumbsDown, RotateCcw, Check } from "lucide-react";
import type { Message } from "../types";
import { ToolCallCard } from "./ToolCallCard";
import { ClaudeLogo } from "./ClaudeLogo";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const [copied, setCopied] = useState(false);

  const calls = message.toolCalls?.filter((e) => e.type === "tool_call") ?? [];
  const obs = message.toolCalls?.filter((e) => e.type === "observation") ?? [];

  function handleCopy() {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  if (message.role === "user") {
    return (
      <div className="msg-user-wrap">
        <div className="msg-user-bubble">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="msg-assistant-wrap">
      <div className="msg-assistant-logo">
        <ClaudeLogo size={20} />
      </div>
      <div className="msg-assistant-body">
        {calls.map((tc, j) => (
          <ToolCallCard key={j} toolCall={tc} observation={obs[j]} />
        ))}
        <div className="msg-assistant-content">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {message.content && (
          <div className="msg-reactions">
            <button className="msg-reaction-btn" onClick={handleCopy} title="Copy" aria-label={copied ? "Copied" : "Copy response"}>
              {copied ? <Check size={14} strokeWidth={2} /> : <Copy size={14} strokeWidth={1.8} />}
            </button>
            <button className="msg-reaction-btn" title="Good response" aria-label="Mark as helpful">
              <ThumbsUp size={14} strokeWidth={1.8} />
            </button>
            <button className="msg-reaction-btn" title="Bad response" aria-label="Mark as unhelpful">
              <ThumbsDown size={14} strokeWidth={1.8} />
            </button>
            <button className="msg-reaction-btn" title="Retry" aria-label="Regenerate response">
              <RotateCcw size={14} strokeWidth={1.8} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
