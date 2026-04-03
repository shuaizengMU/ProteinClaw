import React, { useEffect, useState } from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"
import useInput from "../ink/hooks/use-input.js"
import { useAppState, useDispatch } from "../state/selectors.js"
import { loadConfig, needsSetup } from "../services/config.js"

type CheckStatus = "pending" | "ok" | "fail"

interface Check { label: string; status: CheckStatus; detail?: string }

export function Doctor() {
  const serverPort = useAppState(s => s.serverPort)
  const wsStatus   = useAppState(s => s.wsStatus)
  const dispatch   = useDispatch()

  const [checks, setChecks] = useState<Check[]>([
    { label: "Config file",        status: "pending" },
    { label: "Python server",      status: "pending" },
    { label: "WebSocket",          status: "pending" },
    { label: "API key configured", status: "pending" },
  ])

  useEffect(() => {
    const cfg = loadConfig()
    const configOk = !needsSetup(cfg)

    setChecks(c => c.map(ch => {
      if (ch.label === "Config file")
        return { ...ch, status: configOk ? "ok" : "fail", detail: configOk ? undefined : "Run setup to configure" }
      if (ch.label === "API key configured")
        return { ...ch, status: configOk ? "ok" : "fail" }
      if (ch.label === "Python server")
        return { ...ch, status: serverPort ? "ok" : "fail", detail: serverPort ? `port ${serverPort}` : "not running" }
      if (ch.label === "WebSocket")
        return { ...ch, status: wsStatus === "connected" ? "ok" : "fail", detail: wsStatus }
      return ch
    }))
  }, [serverPort, wsStatus])

  useInput((_, key) => {
    if (key.escape || key.return) dispatch({ type: "SET_VIEW", view: "repl" })
  })

  const icon  = (s: CheckStatus) => s === "ok" ? "✔" : s === "fail" ? "✖" : "…"
  const color = (s: CheckStatus) => s === "ok" ? "green" : s === "fail" ? "red" : "yellow"

  return (
    <Box flexDirection="column" padding={2} gap={1}>
      <Text bold>ProteinClaw Diagnostics</Text>
      {checks.map(ch => (
        <Box key={ch.label} gap={2}>
          <Text color={color(ch.status)}>{icon(ch.status)}</Text>
          <Text>{ch.label}</Text>
          {ch.detail && <Text dimColor>{ch.detail}</Text>}
        </Box>
      ))}
      <Text dimColor>Press Esc or Enter to return to REPL</Text>
    </Box>
  )
}
