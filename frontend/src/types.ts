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

// Alias for spec compatibility — same shape as ChatMessage
export type Message = ChatMessage;

export interface Project {
  id: string;           // crypto.randomUUID()
  name: string;
  createdAt: number;    // Unix timestamp ms
  conversations: Conversation[];
}

export interface Conversation {
  id: string;
  title: string;        // First user message truncated to 60 chars; starts as "New Chat"
  model: string;
  createdAt: number;
  messages: Message[];
}
