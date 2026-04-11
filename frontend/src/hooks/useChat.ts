declare global {
  interface Window {
    __BACKEND_PORT__?: number;
  }
}

import { useState, useCallback, useEffect, useRef } from "react";
import type { Message, WsEvent, SendPayload } from "../types";

const port = window.__BACKEND_PORT__ ?? 8000;
const WS_URL = `ws://localhost:${port}/ws/chat`;

/**
 * Manages the active WebSocket session.
 *
 * onMessage is called at logical boundaries only (not per token):
 *   1. Immediately with the user message when send() is called.
 *   2. Once with the final assistant message when WS closes (done/error).
 *
 * streamingAssistant holds the in-progress assistant message for live display.
 * It becomes null in the same React batch as the onMessage(assistantMsg) call,
 * so the persisted message and cleared streaming state render together (no flash).
 */
export function useChat(
  conversationId: string,
  onMessage: (msg: Message) => void
) {
  const [streamingAssistant, setStreamingAssistant] = useState<Message | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  // Always call the latest onMessage without adding it to send's deps
  const onMessageRef = useRef(onMessage);
  useEffect(() => {
    onMessageRef.current = onMessage;
  });

  // Track open WS so we can close it on conversation switch
  const wsRef = useRef<WebSocket | null>(null);

  // Reset streaming state when conversation changes
  useEffect(() => {
    setStreamingAssistant(null);
    setLoading(false);
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [conversationId]);

  const send = useCallback(
    (
      text: string,
      model: string,
      history: Array<{ role: string; content: string }>
    ) => {
      setLoading(true);

      // Persist user message immediately
      onMessageRef.current({ role: "user", content: text });

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      let currentContent = "";
      let currentToolCalls: WsEvent[] = [];

      // Get API key from localStorage if configured
      const apiKeyMap: Record<string, string> = {
        "claude-opus-4-5": "ANTHROPIC_API_KEY",
        "claude-sonnet-4-6": "ANTHROPIC_API_KEY",
        "gpt-4o": "OPENAI_API_KEY",
        "deepseek-chat": "DEEPSEEK_API_KEY",
        "deepseek-reasoner": "DEEPSEEK_API_KEY",
        "ollama/llama3": "OLLAMA_BASE_URL",
      };

      const configKey = apiKeyMap[model];
      const apiKey = configKey ? localStorage.getItem(configKey) : null;

      const payload: any = { message: text, model, history };
      if (apiKey) {
        payload.api_key = apiKey;
        payload.config_key = configKey;
      }
      ws.onopen = () => ws.send(JSON.stringify(payload));

      ws.onmessage = (e) => {
        const event: WsEvent = JSON.parse(e.data);

        if (event.type === "thinking") {
          currentContent += `\n_${event.content}_`;
        } else if (
          event.type === "tool_call" ||
          event.type === "observation"
        ) {
          currentToolCalls = [...currentToolCalls, event];
        } else if (event.type === "token") {
          currentContent += event.content ?? "";
        } else if (event.type === "error") {
          currentContent += `\n[Error: ${event.message}]`;
        }

        const assistantMsg: Message = {
          role: "assistant",
          content: currentContent,
          toolCalls: currentToolCalls,
        };
        setStreamingAssistant(assistantMsg);

        if (event.type === "done" || event.type === "error") {
          // Batched with setStreamingAssistant(null) — single render, no flash
          onMessageRef.current(assistantMsg);
          setStreamingAssistant(null);
          setLoading(false);
          ws.close();
          wsRef.current = null;
        }
      };

      ws.onerror = () => {
        const errMsg: Message = {
          role: "assistant",
          content: "[WebSocket connection error]",
          toolCalls: [],
        };
        onMessageRef.current(errMsg);
        setStreamingAssistant(null);
        setLoading(false);
        wsRef.current = null;
      };
    },
    [] // no deps — uses refs for everything that could change
  );

  return { loading, send, streamingAssistant };
}
