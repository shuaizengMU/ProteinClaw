/**
 * Collapsible thinking block — mirrors Claude Code's AssistantThinkingMessage.
 * Collapsed:  ∴ Thinking  (ctrl+o to expand)
 * Expanded:   ∴ Thinking…
 *             <markdown content>
 */
import React, { useState } from 'react'
import Box from '../ink/components/Box.js'
import Text from '../ink/components/Text.js'
import useInput from '../ink/hooks/use-input.js'
import { Markdown } from './Markdown.js'

interface Props {
  content: string
  addMargin?: boolean
}

export function ThinkingBlock({ content, addMargin = false }: Props) {
  const [expanded, setExpanded] = useState(false)

  useInput((_, key) => {
    if (key.ctrl && _ === 'o') setExpanded(v => !v)
  })

  if (!content) return null

  if (!expanded) {
    return (
      <Box marginTop={addMargin ? 1 : 0}>
        <Text dimColor italic>∴ Thinking </Text>
        <Text dimColor>(ctrl+o to expand)</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column" gap={1} marginTop={addMargin ? 1 : 0} width="100%">
      <Text dimColor italic>∴ Thinking…</Text>
      <Box paddingLeft={2}>
        <Markdown dimColor>{content}</Markdown>
      </Box>
    </Box>
  )
}
