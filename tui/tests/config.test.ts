import { describe, test, expect, beforeEach, afterEach } from "bun:test"
import { mkdtempSync, rmSync } from "fs"
import { join } from "path"
import { tmpdir } from "os"
import {
  loadConfig,
  saveConfig,
  needsSetup,
  PROVIDERS,
  modelsForProvider,
} from "../src/services/config"

describe("config", () => {
  let tmpDir: string
  let cfgPath: string

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), "pcc-test-"))
    cfgPath = join(tmpDir, "config.toml")
  })

  afterEach(() => {
    rmSync(tmpDir, { recursive: true })
  })

  test("loadConfig returns defaults when file missing", () => {
    const cfg = loadConfig(cfgPath)
    expect(cfg.defaultModel).toBe("gpt-4o")
    expect(cfg.keys).toEqual({})
  })

  test("save and load roundtrip", () => {
    saveConfig({ keys: { DEEPSEEK_API_KEY: "sk-abc" }, defaultModel: "deepseek-chat" }, cfgPath)
    const loaded = loadConfig(cfgPath)
    expect(loaded.defaultModel).toBe("deepseek-chat")
    expect(loaded.keys["DEEPSEEK_API_KEY"]).toBe("sk-abc")
  })

  test("needsSetup true when key missing for deepseek", () => {
    expect(needsSetup({ keys: {}, defaultModel: "deepseek-chat" })).toBe(true)
  })

  test("needsSetup false when key present", () => {
    expect(needsSetup({ keys: { DEEPSEEK_API_KEY: "sk-x" }, defaultModel: "deepseek-chat" })).toBe(false)
  })

  test("needsSetup false for ollama (no key required)", () => {
    expect(needsSetup({ keys: {}, defaultModel: "ollama/llama3" })).toBe(false)
  })

  test("needsSetup true for anthropic without key", () => {
    expect(needsSetup({ keys: {}, defaultModel: "claude-opus-4-5" })).toBe(true)
  })

  test("PROVIDERS contains 5 entries", () => {
    expect(PROVIDERS).toHaveLength(5)
  })

  test("modelsForProvider returns models for deepseek", () => {
    expect(modelsForProvider("deepseek")).toEqual(["deepseek-chat", "deepseek-reasoner"])
  })

  test("empty key values are excluded from loaded config", () => {
    const { writeFileSync } = require("fs")
    writeFileSync(cfgPath, '[keys]\nDEEPSEEK_API_KEY = ""\n[defaults]\nmodel = "gpt-4o"\n')
    const cfg = loadConfig(cfgPath)
    expect(cfg.keys["DEEPSEEK_API_KEY"]).toBeUndefined()
  })
})
