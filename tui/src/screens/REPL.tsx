import React, { useEffect } from "react"
import Box from "../ink/components/Box.js"
import { useAppState, useDispatch } from "../state/selectors.js"
import { StatusBar }          from "../components/StatusBar.js"
import { VirtualMessageList } from "../components/VirtualMessageList.js"
import { PromptInput }        from "../components/PromptInput.js"
import type { WsClient }      from "../services/ws.js"

interface Props {
  ws: WsClient
}

export function REPL({ ws }: Props) {
  const messages = useAppState(s => s.messages)
  const dispatch = useDispatch()

  useEffect(() => {
    const offEvent = ws.onEvent(event => {
      switch (event.type) {
        case "token":       dispatch({ type: "TOKEN",       content: event.content }); break
        case "thinking":    dispatch({ type: "THINKING",    content: event.content }); break
        case "tool_call":   dispatch({ type: "TOOL_CALL",   tool: event.tool, args: event.args }); break
        case "observation": dispatch({ type: "OBSERVATION", result: event.result }); break
        case "done":        dispatch({ type: "DONE" }); break
        case "error":       dispatch({ type: "ERROR",       message: event.message }); break
      }
    })

    const offStatus = ws.onStatus(status => {
      dispatch({ type: "WS_STATUS", status })
    })

    return () => { offEvent(); offStatus() }
  }, [ws, dispatch])

  return (
    <Box flexDirection="column" height="100%">
      <StatusBar />
      <VirtualMessageList messages={messages} />
      <PromptInput ws={ws} />
    </Box>
  )
}
