import React, { useState } from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"

interface Props {
  tool: string
  args: unknown
  result?: unknown
}

export function ToolCallCard({ tool, args, result }: Props) {
  const [expanded, setExpanded] = useState(false)
  const argsStr   = JSON.stringify(args, null, 2)
  const resultStr = result !== undefined ? JSON.stringify(result, null, 2) : null

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text color="cyan" bold>⚙ {tool}</Text>
      {expanded && (
        <Box flexDirection="column">
          <Text color="cyan" dimColor>args: {argsStr}</Text>
          {resultStr
            ? <Text color="cyan">result: {resultStr.length > 200 ? resultStr.slice(0, 200) + "…" : resultStr}</Text>
            : <Text color="gray" dimColor>(waiting for result…)</Text>
          }
        </Box>
      )}
    </Box>
  )
}
