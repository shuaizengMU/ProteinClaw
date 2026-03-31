export type AgentEvent =
  | { type: "token";       content: string }
  | { type: "thinking";    content: string }
  | { type: "tool_call";   tool: string; args: unknown }
  | { type: "observation"; result: unknown }
  | { type: "done" }
  | { type: "error";       message: string }

export interface WsQuery {
  message: string
  history: { role: string; content: string }[]
  model: string
}

export type WsStatus = "connecting" | "connected" | "error" | "closed"

export function parseAgentEvent(json: string): AgentEvent | null {
  try {
    const raw = JSON.parse(json)
    switch (raw.type) {
      case "token":       return { type: "token",       content: raw.content ?? "" }
      case "thinking":    return { type: "thinking",    content: raw.content ?? "" }
      case "tool_call":   return { type: "tool_call",   tool: raw.tool ?? "", args: raw.args ?? null }
      case "observation": return { type: "observation", result: raw.result ?? null }
      case "done":        return { type: "done" }
      case "error":       return { type: "error",       message: raw.message ?? "" }
      default:            return null
    }
  } catch {
    return null
  }
}

export interface WsClient {
  send(query: WsQuery): void
  close(): void
  onEvent(handler: (event: AgentEvent) => void): () => void
  onStatus(handler: (status: WsStatus) => void): () => void
}

export function createWsClient(port: number): WsClient {
  const eventHandlers = new Set<(e: AgentEvent) => void>()
  const statusHandlers = new Set<(s: WsStatus) => void>()
  let ws: WebSocket | null = null
  let reconnectDelay = 1000
  let closed = false
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function emit(status: WsStatus) { statusHandlers.forEach(h => h(status)) }

  function connect() {
    ws = new WebSocket(`ws://127.0.0.1:${port}/ws/chat`)

    ws.onopen = () => {
      reconnectDelay = 1000
      emit("connected")
    }

    ws.onmessage = (e) => {
      const event = parseAgentEvent(String(e.data))
      if (event) eventHandlers.forEach(h => h(event))
    }

    ws.onclose = () => {
      if (closed) return
      emit("error")
      reconnectTimer = setTimeout(() => {
        reconnectDelay = Math.min(reconnectDelay * 2, 30_000)
        connect()
      }, reconnectDelay)
    }
  }

  connect()

  return {
    send(query) {
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(query))
    },
    close() {
      closed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
      emit("closed")
    },
    onEvent(h) { eventHandlers.add(h); return () => eventHandlers.delete(h) },
    onStatus(h) { statusHandlers.add(h); return () => statusHandlers.delete(h) },
  }
}
