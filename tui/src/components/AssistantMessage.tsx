import React from 'react'
import Box from '../ink/components/Box.js'
import Text from '../ink/components/Text.js'
import { Markdown } from './Markdown.js'

interface Props {
  content: string
  streaming: boolean
}

export function AssistantMessage({ content, streaming }: Props) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      {streaming
        ? (
          // While streaming: plain text — markdown parser can't handle partial tokens
          <Box>
            <Text>{content}</Text>
            <Text inverse> </Text>
          </Box>
        )
        : <Markdown>{content}</Markdown>
      }
    </Box>
  )
}
