import React from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"
import { useAppState } from "../state/selectors.js"

export function StatusBar() {
  const model    = useAppState(s => s.model)
  const wsStatus = useAppState(s => s.wsStatus)
  const thinking = useAppState(s => s.isThinking)

  const statusColor =
    wsStatus === "connected" ? "green"  :
    wsStatus === "error"     ? "red"    : "yellow"

  return (
    <Box paddingX={1}>
      <Text bold color="white"> ProteinClaw </Text>
      <Text color="white"> │ model: {model} │ </Text>
      <Text color={statusColor}>{wsStatus}</Text>
      {thinking && <Text color="yellow"> │ thinking...</Text>}
    </Box>
  )
}
