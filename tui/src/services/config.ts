import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs"
import { dirname, join } from "path"
import { homedir } from "os"

export interface Config {
  keys: Record<string, string>
  defaultModel: string
}

export interface Provider {
  id: string
  display: string
  envKey: string
}

export const PROVIDERS: Provider[] = [
  { id: "anthropic", display: "Anthropic",                         envKey: "ANTHROPIC_API_KEY" },
  { id: "openai",    display: "OpenAI",                            envKey: "OPENAI_API_KEY" },
  { id: "deepseek",  display: "DeepSeek",                          envKey: "DEEPSEEK_API_KEY" },
  { id: "minimax",   display: "MiniMax",                           envKey: "MINIMAX_API_KEY" },
  { id: "ollama",    display: "Ollama (local, no API key needed)",  envKey: "" },
]

const MODEL_OPTIONS: Record<string, string[]> = {
  anthropic: ["claude-opus-4-5"],
  openai:    ["gpt-4o"],
  deepseek:  ["deepseek-chat", "deepseek-reasoner"],
  minimax:   ["minimax-text-01"],
  ollama:    ["ollama/llama3"],
}

export function modelsForProvider(providerId: string): string[] {
  return MODEL_OPTIONS[providerId] ?? []
}

export function defaultConfigPath(): string {
  const base = process.env["XDG_CONFIG_HOME"] ?? join(homedir(), ".config")
  return join(base, "proteinclaw", "config.toml")
}

/** Minimal TOML parser for our two-section config format only. */
function parseToml(text: string): Record<string, Record<string, string>> {
  const result: Record<string, Record<string, string>> = {}
  let section = ""
  for (const raw of text.split("\n")) {
    const line = raw.trim()
    if (!line || line.startsWith("#")) continue
    const sec = line.match(/^\[(\w+)\]$/)
    if (sec) { section = sec[1]; result[section] ??= {}; continue }
    const kv = line.match(/^(\w+)\s*=\s*"([^"]*)"$/)
    if (kv && section) result[section][kv[1]] = kv[2]
  }
  return result
}

function toToml(config: Config): string {
  const keyLines = Object.entries(config.keys)
    .map(([k, v]) => `${k} = "${v}"`)
    .join("\n")
  return `[keys]\n${keyLines}\n\n[defaults]\nmodel = "${config.defaultModel}"\n`
}

export function loadConfig(path = defaultConfigPath()): Config {
  if (!existsSync(path)) return { keys: {}, defaultModel: "gpt-4o" }
  try {
    const doc = parseToml(readFileSync(path, "utf-8"))
    const keys: Record<string, string> = {}
    for (const [k, v] of Object.entries(doc["keys"] ?? {})) {
      if (v) keys[k] = v
    }
    return { keys, defaultModel: doc["defaults"]?.["model"] ?? "gpt-4o" }
  } catch {
    return { keys: {}, defaultModel: "gpt-4o" }
  }
}

export function saveConfig(config: Config, path = defaultConfigPath()): void {
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, toToml(config), "utf-8")
}

function providerForModel(model: string): string {
  if (model === "gpt-4o") return "openai"
  if (model === "claude-opus-4-5") return "anthropic"
  if (model === "deepseek-chat" || model === "deepseek-reasoner") return "deepseek"
  if (model === "minimax-text-01") return "minimax"
  if (model.startsWith("ollama/")) return "ollama"
  return ""
}

export function needsSetup(config: Config): boolean {
  const provider = providerForModel(config.defaultModel)
  if (provider === "ollama") return false
  const envKey = PROVIDERS.find(p => p.id === provider)?.envKey ?? ""
  if (!envKey) return true
  return !config.keys[envKey]
}
