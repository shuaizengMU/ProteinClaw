import { describe, test, expect } from "bun:test"
import { createAppStore } from "../src/state/AppStateStore"

describe("AppStateStore", () => {
  test("initial state — no setup", () => {
    const store = createAppStore({ defaultModel: "deepseek-chat", needsSetup: false })
    const s = store.getSnapshot()
    expect(s.view).toBe("repl")
    expect(s.model).toBe("deepseek-chat")
    expect(s.messages).toEqual([])
    expect(s.isThinking).toBe(false)
    expect(s.wsStatus).toBe("connecting")
  })

  test("initial state — needs setup", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: true })
    expect(store.getSnapshot().view).toBe("setup")
  })

  test("USER_MESSAGE adds message and sets isThinking", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "USER_MESSAGE", text: "hello" })
    const s = store.getSnapshot()
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0]).toMatchObject({ role: "user", content: "hello" })
    expect(s.isThinking).toBe(true)
    expect(s.history[0]).toEqual({ role: "user", content: "hello" })
  })

  test("TOKEN creates streaming assistant message", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "TOKEN", content: "Hello" })
    const msg = store.getSnapshot().messages[0] as any
    expect(msg.role).toBe("assistant")
    expect(msg.content).toBe("Hello")
    expect(msg.streaming).toBe(true)
  })

  test("consecutive TOKENs accumulate", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "TOKEN", content: "Hello" })
    store.dispatch({ type: "TOKEN", content: " world" })
    expect(store.getSnapshot().messages).toHaveLength(1)
    expect((store.getSnapshot().messages[0] as any).content).toBe("Hello world")
  })

  test("DONE finalizes streaming and clears isThinking", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "TOKEN", content: "Hi" })
    store.dispatch({ type: "DONE" })
    const s = store.getSnapshot()
    expect(s.isThinking).toBe(false)
    expect((s.messages[0] as any).streaming).toBe(false)
    expect(s.history[0]).toEqual({ role: "assistant", content: "Hi" })
  })

  test("TOOL_CALL adds tool message", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "TOOL_CALL", tool: "uniprot", args: { id: "P04637" } })
    const msg = store.getSnapshot().messages[0] as any
    expect(msg.role).toBe("tool_call")
    expect(msg.tool).toBe("uniprot")
    expect(msg.result).toBeUndefined()
  })

  test("OBSERVATION sets result on last tool_call", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "TOOL_CALL", tool: "uniprot", args: {} })
    store.dispatch({ type: "OBSERVATION", result: { name: "TP53" } })
    const msg = store.getSnapshot().messages[0] as any
    expect(msg.result).toEqual({ name: "TP53" })
  })

  test("CLEAR empties messages and history", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "USER_MESSAGE", text: "hi" })
    store.dispatch({ type: "CLEAR" })
    const s = store.getSnapshot()
    expect(s.messages).toHaveLength(0)
    expect(s.history).toHaveLength(0)
    expect(s.isThinking).toBe(false)
  })

  test("SET_MODEL updates model", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "SET_MODEL", model: "deepseek-chat" })
    expect(store.getSnapshot().model).toBe("deepseek-chat")
  })

  test("WS_STATUS updates status", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "WS_STATUS", status: "connected" })
    expect(store.getSnapshot().wsStatus).toBe("connected")
  })

  test("subscribers notified on change, removed on unsub", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    let count = 0
    const unsub = store.subscribe(() => count++)
    store.dispatch({ type: "WS_STATUS", status: "connected" })
    expect(count).toBe(1)
    unsub()
    store.dispatch({ type: "WS_STATUS", status: "error" })
    expect(count).toBe(1)
  })

  test("ERROR adds error message and clears isThinking", () => {
    const store = createAppStore({ defaultModel: "gpt-4o", needsSetup: false })
    store.dispatch({ type: "USER_MESSAGE", text: "hi" })
    store.dispatch({ type: "ERROR", message: "API error" })
    const s = store.getSnapshot()
    expect(s.isThinking).toBe(false)
    expect((s.messages[1] as any).role).toBe("error")
    expect((s.messages[1] as any).content).toBe("API error")
  })
})
