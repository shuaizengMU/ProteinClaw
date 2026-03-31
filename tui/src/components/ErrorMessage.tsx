import React from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"

export function ErrorMessage({ content }: { content: string }) {
  return (
    <Box marginBottom={1}>
      <Text color="red">✖ {content}</Text>
    </Box>
  )
}
