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

export type Message = ChatMessage;

// Stored in index.json — no messages
export interface ConversationMeta {
  id: string;
  title: string;
  model: string;
  createdAt: number;
  pinned?: boolean;
}

// Stored in conversations/{id}.json
export interface ConversationMessages {
  id: string;
  messages: Message[];
}

// Combined in memory for use across the app
export interface Conversation extends ConversationMeta {
  messages: Message[];
}

export interface Project {
  id: string;
  name: string;
  createdAt: number;
  folderPath?: string;
  conversations: ConversationMeta[];
}

export type CaseStudyCategoryId = 'sequence' | 'structure' | 'drug' | 'function' | 'annotation' | 'variants' | 'disease' | 'pathways' | 'expression' | 'genomics' | 'literature';

export interface CaseStudyCategory {
  id: CaseStudyCategoryId | 'all';
  label: string;
  color: string;
}

export interface CaseStudy {
  id: string;
  title: string;
  category: CaseStudyCategoryId;
  icon: string;
  description: string;
  examplePrompt: string;
  exampleResult: string;
}
