import { useState, useRef, useEffect } from "react";
import type { ChatMessage } from "../types";
import { ToolCallCard } from "./ToolCallCard";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (text: string) => void;
}

export function ChatWindow({ messages, loading, onSend }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", maxWidth: 800, margin: "0 auto" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {msg.role === "user" ? "You" : "ProteinClaw"}
            </div>

            {msg.toolCalls && (() => {
              const calls = msg.toolCalls.filter((e) => e.type === "tool_call");
              const obs = msg.toolCalls.filter((e) => e.type === "observation");
              return calls.map((tc, j) => (
                <ToolCallCard key={j} toolCall={tc} observation={obs[j]} />
              ));
            })()}

            <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
          </div>
        ))}
        {loading && <div style={{ color: "#888", fontStyle: "italic" }}>ProteinClaw is thinking...</div>}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", padding: 16, borderTop: "1px solid #ddd" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a protein, e.g. 'What is P04637?'"
          disabled={loading}
          style={{ flex: 1, padding: "8px 12px", fontSize: 14, borderRadius: 4, border: "1px solid #ccc" }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{ marginLeft: 8, padding: "8px 16px", borderRadius: 4, cursor: "pointer" }}
        >
          Send
        </button>
      </form>
    </div>
  );
}
