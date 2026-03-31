import React from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"

export function AssistantMessage({ content, streaming }: { content: string; streaming: boolean }) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text>{content}{streaming ? "▋" : ""}</Text>
    </Box>
  )
}
