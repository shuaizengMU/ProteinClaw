/**
 * Tool call card — mirrors Claude Code's AssistantToolUseMessage visual style.
 * Shows tool name with status indicator: ⏺ in-progress, ✔ resolved, ○ queued.
 */
import React, { useState } from 'react'
import Box from '../ink/components/Box.js'
import Text from '../ink/components/Text.js'
import useInput from '../ink/hooks/use-input.js'

interface Props {
  tool: string
  args: unknown
  result?: unknown
}

function formatJson(v: unknown, maxLen = 300): string {
  const s = JSON.stringify(v, null, 2)
  return s.length > maxLen ? s.slice(0, maxLen) + '…' : s
}

export function ToolCallCard({ tool, args, result }: Props) {
  const [expanded, setExpanded] = useState(false)

  useInput((_, key) => {
    if (key.return) setExpanded(v => !v)
  })

  const isResolved = result !== undefined
  const statusChar  = isResolved ? '⏺' : '⏺'
  const statusColor = isResolved ? 'green' : 'yellow'

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box gap={1}>
        <Text color={statusColor}>{statusChar}</Text>
        <Text bold>{tool}</Text>
        {!expanded && (
          <Text dimColor>
            {isResolved ? '— done' : '— running…'}
          </Text>
        )}
      </Box>

      {expanded && (
        <Box flexDirection="column" paddingLeft={2} gap={1}>
          <Text dimColor>Input: <Text color="cyan">{formatJson(args)}</Text></Text>
          {isResolved
            ? <Text dimColor>Result: <Text>{formatJson(result)}</Text></Text>
            : <Text dimColor italic>Waiting for result…</Text>
          }
        </Box>
      )}
    </Box>
  )
}
