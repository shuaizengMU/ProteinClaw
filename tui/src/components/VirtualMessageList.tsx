import React from "react"
import Box from "../ink/components/Box.js"
import type { Message } from "../state/AppStateStore.js"
import { UserMessage }      from "./UserMessage.js"
import { AssistantMessage } from "./AssistantMessage.js"
import { ThinkingBlock }    from "./ThinkingBlock.js"
import { ToolCallCard }     from "./ToolCallCard.js"
import { ErrorMessage }     from "./ErrorMessage.js"

function MessageRow({ msg }: { msg: Message }) {
  switch (msg.role) {
    case "user":      return <UserMessage content={msg.content} />
    case "assistant": return <AssistantMessage content={msg.content} streaming={msg.streaming} />
    case "thinking":  return <ThinkingBlock content={msg.content} />
    case "tool_call": return <ToolCallCard tool={msg.tool} args={msg.args} result={msg.result} />
    case "error":     return <ErrorMessage content={msg.content} />
  }
}

export function VirtualMessageList({ messages }: { messages: Message[] }) {
  return (
    <Box flexDirection="column" flexGrow={1}>
      {messages.map((msg, i) => <MessageRow key={i} msg={msg} />)}
    </Box>
  )
}
