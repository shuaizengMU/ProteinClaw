/**
 * User message — mirrors Claude Code's UserPromptMessage visual style.
 * Bold color with a leading > sigil.
 */
import React from 'react'
import Box from '../ink/components/Box.js'
import Text from '../ink/components/Text.js'

export function UserMessage({ content }: { content: string }) {
  return (
    <Box flexDirection="column" marginTop={1} marginBottom={1}>
      <Box gap={1}>
        <Text bold color="greenBright">{'>'}</Text>
        <Text bold>{content}</Text>
      </Box>
    </Box>
  )
}
