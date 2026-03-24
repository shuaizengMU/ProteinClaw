export type WsEventType =
  | "thinking"
  | "tool_call"
  | "observation"
  | "token"
  | "done"
  | "error";

export interface WsEvent {
  type: WsEventType;
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
  message?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: WsEvent[];
}

export interface SendPayload {
  message: string;
  model: string;
  history: Array<{ role: string; content: string }>;
}
