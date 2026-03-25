declare global {
  interface Window {
    __BACKEND_PORT__?: number;
  }
}

import { useState, useCallback } from "react";
import type { ChatMessage, WsEvent, SendPayload } from "../types";

const port = window.__BACKEND_PORT__ ?? 8000;
const WS_URL = `ws://localhost:${port}/ws/chat`;

let msgIdCounter = 0;

interface TrackedMessage extends ChatMessage {
  id: number;
}

export function useChat() {
  const [messages, setMessages] = useState<TrackedMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const send = useCallback((text: string, model: string) => {
    setLoading(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    const userMsg: TrackedMessage = { id: msgIdCounter++, role: "user", content: text };
    const assistantId = msgIdCounter++;
    const assistantMsg: TrackedMessage = { id: assistantId, role: "assistant", content: "", toolCalls: [] };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const ws = new WebSocket(WS_URL);

    const payload: SendPayload = { message: text, model, history };
    ws.onopen = () => ws.send(JSON.stringify(payload));

    ws.onmessage = (e) => {
      const event: WsEvent = JSON.parse(e.data);

      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== assistantId) return msg;
          const updated = { ...msg };
          if (event.type === "thinking") {
            updated.content += `\n_${event.content}_`;
          } else if (event.type === "tool_call" || event.type === "observation") {
            updated.toolCalls = [...(updated.toolCalls ?? []), event];
          } else if (event.type === "token") {
            updated.content += event.content ?? "";
          } else if (event.type === "error") {
            updated.content += `\n[Error: ${event.message}]`;
          }
          return updated;
        })
      );

      if (event.type === "done" || event.type === "error") {
        setLoading(false);
        ws.close();
      }
    };

    ws.onerror = () => {
      setLoading(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: "[WebSocket connection error]" }
            : msg
        )
      );
    };
  }, [messages]);

  return { messages, loading, send };
}
