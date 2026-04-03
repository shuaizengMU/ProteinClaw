import { describe, test, expect } from "bun:test"
import { parseAgentEvent } from "../src/services/ws"

describe("parseAgentEvent", () => {
  test("token event", () => {
    expect(parseAgentEvent('{"type":"token","content":"Hello"}')).toEqual({
      type: "token", content: "Hello",
    })
  })

  test("thinking event", () => {
    expect(parseAgentEvent('{"type":"thinking","content":"Analyzing..."}')).toEqual({
      type: "thinking", content: "Analyzing...",
    })
  })

  test("tool_call event", () => {
    expect(parseAgentEvent('{"type":"tool_call","tool":"uniprot","args":{"id":"P04637"}}')).toEqual({
      type: "tool_call", tool: "uniprot", args: { id: "P04637" },
    })
  })

  test("observation event", () => {
    expect(parseAgentEvent('{"type":"observation","result":{"name":"TP53"}}')).toEqual({
      type: "observation", result: { name: "TP53" },
    })
  })

  test("done event", () => {
    expect(parseAgentEvent('{"type":"done"}')).toEqual({ type: "done" })
  })

  test("error event", () => {
    expect(parseAgentEvent('{"type":"error","message":"API key missing"}')).toEqual({
      type: "error", message: "API key missing",
    })
  })

  test("unknown type returns null", () => {
    expect(parseAgentEvent('{"type":"unknown"}')).toBeNull()
  })

  test("invalid JSON returns null", () => {
    expect(parseAgentEvent("not json")).toBeNull()
  })

  test("missing content defaults to empty string", () => {
    expect(parseAgentEvent('{"type":"token"}')).toEqual({ type: "token", content: "" })
  })
})
