import React, { useState } from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"

export function ThinkingBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text color="gray" dimColor>
        {expanded ? "▼ thinking" : "▶ thinking"}
      </Text>
      {expanded && <Text color="gray">{content}</Text>}
    </Box>
  )
}
