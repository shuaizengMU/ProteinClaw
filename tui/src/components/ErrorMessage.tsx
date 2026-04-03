import React from 'react'
import Box from '../ink/components/Box.js'
import Text from '../ink/components/Text.js'

export function ErrorMessage({ content }: { content: string }) {
  return (
    <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
      <Text color="red" bold>✗ Error</Text>
      <Box paddingLeft={2}>
        <Text color="red">{content}</Text>
      </Box>
    </Box>
  )
}
