import type { WsStatus } from "../services/ws"

export type AppView = "repl" | "setup" | "doctor"

export interface UserMessage    { role: "user";      content: string }
export interface AssistantMsg   { role: "assistant"; content: string; streaming: boolean }
export interface ThinkingMsg    { role: "thinking";  content: string }
export interface ToolCallMsg    { role: "tool_call"; tool: string; args: unknown; result?: unknown }
export interface ErrorMsg       { role: "error";     content: string }

export type Message = UserMessage | AssistantMsg | ThinkingMsg | ToolCallMsg | ErrorMsg

export interface HistoryEntry { role: string; content: string }

export interface AppState {
  view: AppView
  messages: Message[]
  history: HistoryEntry[]
  model: string
  isThinking: boolean
  wsStatus: WsStatus
  serverPort: number | null
}

export type AppAction =
  | { type: "USER_MESSAGE"; text: string }
  | { type: "TOKEN";        content: string }
  | { type: "THINKING";     content: string }
  | { type: "TOOL_CALL";    tool: string; args: unknown }
  | { type: "OBSERVATION";  result: unknown }
  | { type: "DONE" }
  | { type: "ERROR";        message: string }
  | { type: "CLEAR" }
  | { type: "SET_MODEL";    model: string }
  | { type: "SET_VIEW";     view: AppView }
  | { type: "WS_STATUS";    status: WsStatus }
  | { type: "SERVER_PORT";  port: number }

export interface AppStore {
  getSnapshot(): AppState
  subscribe(listener: () => void): () => void
  dispatch(action: AppAction): void
}

export function createAppStore(init: { defaultModel: string; needsSetup: boolean }): AppStore {
  let state: AppState = {
    view: init.needsSetup ? "setup" : "repl",
    messages: [],
    history: [],
    model: init.defaultModel,
    isThinking: false,
    wsStatus: "connecting",
    serverPort: null,
  }

  const listeners = new Set<() => void>()

  function setState(next: AppState) {
    state = next
    listeners.forEach(l => l())
  }

  function dispatch(action: AppAction) {
    const s = state
    switch (action.type) {
      case "USER_MESSAGE":
        setState({
          ...s,
          isThinking: true,
          messages: [...s.messages, { role: "user", content: action.text }],
          history:  [...s.history,  { role: "user", content: action.text }],
        })
        break

      case "TOKEN": {
        const last = s.messages[s.messages.length - 1]
        if (last?.role === "assistant" && (last as AssistantMsg).streaming) {
          const updated: AssistantMsg = { ...last as AssistantMsg, content: last.content + action.content }
          setState({ ...s, messages: [...s.messages.slice(0, -1), updated] })
        } else {
          setState({ ...s, messages: [...s.messages, { role: "assistant", content: action.content, streaming: true }] })
        }
        break
      }

      case "THINKING":
        setState({ ...s, messages: [...s.messages, { role: "thinking", content: action.content }] })
        break

      case "TOOL_CALL":
        setState({ ...s, messages: [...s.messages, { role: "tool_call", tool: action.tool, args: action.args }] })
        break

      case "OBSERVATION": {
        const messages = [...s.messages]
        for (let i = messages.length - 1; i >= 0; i--) {
          const m = messages[i] as ToolCallMsg
          if (m.role === "tool_call" && m.result === undefined) {
            messages[i] = { ...m, result: action.result }
            break
          }
        }
        setState({ ...s, messages })
        break
      }

      case "DONE": {
        const last = s.messages[s.messages.length - 1]
        const messages = (last?.role === "assistant" && (last as AssistantMsg).streaming)
          ? [...s.messages.slice(0, -1), { ...last as AssistantMsg, streaming: false }]
          : s.messages
        const finalContent = (messages.filter(m => m.role === "assistant").slice(-1)[0] as AssistantMsg | undefined)?.content
        const history = finalContent ? [...s.history, { role: "assistant", content: finalContent }] : s.history
        setState({ ...s, messages, history, isThinking: false })
        break
      }

      case "ERROR":
        setState({ ...s, isThinking: false, messages: [...s.messages, { role: "error", content: action.message }] })
        break

      case "CLEAR":
        setState({ ...s, messages: [], history: [], isThinking: false })
        break

      case "SET_MODEL":
        setState({ ...s, model: action.model })
        break

      case "SET_VIEW":
        setState({ ...s, view: action.view })
        break

      case "WS_STATUS":
        setState({ ...s, wsStatus: action.status })
        break

      case "SERVER_PORT":
        setState({ ...s, serverPort: action.port })
        break
    }
  }

  return {
    getSnapshot: () => state,
    subscribe:   (l) => { listeners.add(l); return () => listeners.delete(l) },
    dispatch,
  }
}
