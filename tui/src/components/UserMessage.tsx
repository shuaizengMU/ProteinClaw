import React from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"

export function UserMessage({ content }: { content: string }) {
  return (
    <Box flexDirection="column" marginY={1}>
      <Text bold color="blue">{">"} {content}</Text>
    </Box>
  )
}
