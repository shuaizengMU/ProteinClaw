import React, { useState } from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"
import useInput from "../ink/hooks/use-input.js"
import { PROVIDERS, modelsForProvider, saveConfig } from "../services/config.js"
import { useDispatch } from "../state/selectors.js"

type SetupStep = "welcome" | "provider" | "apikey" | "model"

export function Setup() {
  const [step, setStep]               = useState<SetupStep>("welcome")
  const [providerIdx, setProviderIdx] = useState(0)
  const [apiKey, setApiKey]           = useState("")
  const [cursor, setCursor]           = useState(0)
  const [modelIdx, setModelIdx]       = useState(0)
  const dispatch = useDispatch()

  const selectedProvider = PROVIDERS[providerIdx]
  const models = modelsForProvider(selectedProvider?.id ?? "")

  useInput((char, key) => {
    if (key.escape) return

    if (step === "welcome") {
      if (key.return) setStep("provider")
      return
    }

    if (step === "provider") {
      if (key.upArrow)   setProviderIdx(i => Math.max(0, i - 1))
      if (key.downArrow) setProviderIdx(i => Math.min(PROVIDERS.length - 1, i + 1))
      if (key.return)    setStep(selectedProvider?.envKey ? "apikey" : "model")
      return
    }

    if (step === "apikey") {
      if (key.return) { setStep("model"); return }
      if (key.backspace || key.delete) {
        if (cursor > 0) { setApiKey(k => k.slice(0, cursor - 1) + k.slice(cursor)); setCursor(c => c - 1) }
        return
      }
      if (char && !key.ctrl) {
        setApiKey(k => k.slice(0, cursor) + char + k.slice(cursor))
        setCursor(c => c + 1)
      }
      return
    }

    if (step === "model") {
      if (key.upArrow)   setModelIdx(i => Math.max(0, i - 1))
      if (key.downArrow) setModelIdx(i => Math.min(models.length - 1, i + 1))
      if (key.return) {
        const chosenModel = models[modelIdx] ?? "gpt-4o"
        const keys: Record<string, string> = {}
        if (apiKey && selectedProvider?.envKey) keys[selectedProvider.envKey] = apiKey
        saveConfig({ keys, defaultModel: chosenModel })
        dispatch({ type: "SET_MODEL", model: chosenModel })
        dispatch({ type: "SET_VIEW",  view: "repl" })
      }
      return
    }
  })

  return (
    <Box flexDirection="column" padding={2}>
      <Text bold color="green">{`
  ____            _        _         ____ _
 |  _ \\ _ __ ___ | |_ ___ (_)_ __   / ___| | __ ___      __
 | |_) | '__/ _ \\| __/ _ \\| | '_ \\ | |   | |/ _' \\ \\ /\\ / /
 |  __/| | | (_) | ||  __/| | | | || |___| | (_| |\\ V  V /
 |_|   |_|  \\___/ \\__\\___|_|_| |_| \\____|_|\\__,_| \\_/\\_/
`}</Text>

      {step === "welcome" && (
        <Box flexDirection="column" gap={1}>
          <Text>Welcome to ProteinClaw — AI-powered protein analysis in your terminal.</Text>
          <Text dimColor>Press Enter to set up your API key.</Text>
        </Box>
      )}

      {step === "provider" && (
        <Box flexDirection="column" gap={1}>
          <Text bold>Select your AI provider:</Text>
          {PROVIDERS.map((p, i) => (
            <Text key={p.id} color={i === providerIdx ? "green" : undefined}>
              {i === providerIdx ? "▶ " : "  "}{p.display}
            </Text>
          ))}
          <Text dimColor>↑↓ to select, Enter to confirm</Text>
        </Box>
      )}

      {step === "apikey" && (
        <Box flexDirection="column" gap={1}>
          <Text bold>Enter your {selectedProvider?.display} API key:</Text>
          <Box>
            <Text>{"•".repeat(cursor)}</Text>
            <Text backgroundColor="white" color="black"> </Text>
            <Text>{"•".repeat(Math.max(0, apiKey.length - cursor))}</Text>
          </Box>
          <Text dimColor>Key is masked. Press Enter to continue.</Text>
        </Box>
      )}

      {step === "model" && (
        <Box flexDirection="column" gap={1}>
          <Text bold>Select default model:</Text>
          {models.map((m, i) => (
            <Text key={m} color={i === modelIdx ? "green" : undefined}>
              {i === modelIdx ? "▶ " : "  "}{m}
            </Text>
          ))}
          <Text dimColor>↑↓ to select, Enter to save and start</Text>
        </Box>
      )}
    </Box>
  )
}
