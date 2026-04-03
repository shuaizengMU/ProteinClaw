import { useState, useRef, useEffect } from "react";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";
import { ModelSelector } from "./ModelSelector";

interface Props {
  messages: Message[];
  loading: boolean;
  title: string;
  model: string;
  onModelChange: (m: string) => void;
  onSend: (text: string) => void;
  hasConversation: boolean;
}

export function ChatWindow({
  messages,
  loading,
  title,
  model,
  onModelChange,
  onSend,
  hasConversation,
}: Props) {
  if (!hasConversation) {
    return (
      <div className="chat-window chat-window--empty">
        <div className="empty-state">
          <h2>No conversation selected</h2>
          <p>Create a project in the sidebar, then start a new chat.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-window">
      <TopBar title={title} model={model} onModelChange={onModelChange} />
      <MessageList messages={messages} loading={loading} />
      <InputArea onSend={onSend} loading={loading} />
    </div>
  );
}

function TopBar({
  title,
  model,
  onModelChange,
}: {
  title: string;
  model: string;
  onModelChange: (m: string) => void;
}) {
  return (
    <div className="top-bar">
      <span className="top-bar__title">{title || "New Chat"}</span>
      <ModelSelector value={model} onChange={onModelChange} />
    </div>
  );
}

function MessageList({
  messages,
  loading,
}: {
  messages: Message[];
  loading: boolean;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  function handleScroll() {
    const el = listRef.current;
    if (!el) return;
    isAtBottomRef.current =
      el.scrollTop + el.clientHeight >= el.scrollHeight - 50;
  }

  useEffect(() => {
    const el = listRef.current;
    if (el && isAtBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="message-list" ref={listRef} onScroll={handleScroll}>
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {loading && (
        <div className="thinking-indicator">ProteinClaw is thinking…</div>
      )}
    </div>
  );
}

function InputArea({
  onSend,
  loading,
}: {
  onSend: (text: string) => void;
  loading: boolean;
}) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function adjustHeight() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
  }

  function submit() {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="input-area">
      <textarea
        ref={textareaRef}
        className="input-area__textarea"
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          adjustHeight();
        }}
        onKeyDown={handleKeyDown}
        placeholder="Ask about a protein, e.g. 'What is P04637?'"
        disabled={loading}
        rows={1}
      />
      <button
        className="input-area__submit"
        onClick={submit}
        disabled={loading || !input.trim()}
      >
        {loading ? "…" : "Send"}
      </button>
    </div>
  );
}
