import React, { useState, useCallback } from "react"
import Box from "../ink/components/Box.js"
import Text from "../ink/components/Text.js"
import useInput from "../ink/hooks/use-input.js"
import { useAppState, useDispatch } from "../state/selectors.js"
import type { WsClient } from "../services/ws.js"

interface Props {
  ws: WsClient
}

const SLASH_COMMANDS = ["/clear", "/exit", "/doctor", "/model", "/tools"]

export function PromptInput({ ws }: Props) {
  const [input, setInput]               = useState("")
  const [cursor, setCursor]             = useState(0)
  const [inputHistory, setInputHistory] = useState<string[]>([])
  const [historyIdx, setHistoryIdx]     = useState(-1)

  const model      = useAppState(s => s.model)
  const history    = useAppState(s => s.history)
  const isThinking = useAppState(s => s.isThinking)
  const dispatch   = useDispatch()

  const handleSlash = useCallback((cmd: string) => {
    const parts = cmd.split(/\s+/)
    switch (parts[0]) {
      case "/exit":
        process.exit(0)
        break
      case "/clear":
        dispatch({ type: "CLEAR" })
        break
      case "/doctor":
        dispatch({ type: "SET_VIEW", view: "doctor" })
        break
      case "/model":
        if (parts[1]) {
          dispatch({ type: "SET_MODEL", model: parts[1] })
          dispatch({ type: "USER_MESSAGE", text: `Switched to model: ${parts[1]}` })
          dispatch({ type: "DONE" })
        }
        break
      case "/tools":
        dispatch({ type: "USER_MESSAGE", text: "Available tools: uniprot, blast" })
        dispatch({ type: "DONE" })
        break
      default:
        dispatch({ type: "USER_MESSAGE", text: `Unknown command: ${cmd}. Try: ${SLASH_COMMANDS.join(" ")}` })
        dispatch({ type: "DONE" })
    }
  }, [dispatch])

  const submit = useCallback((text: string) => {
    const query = text.trim()
    if (!query) return

    if (query.startsWith("/")) {
      handleSlash(query)
      return
    }

    setInputHistory(h => [query, ...h.slice(0, 49)])
    setHistoryIdx(-1)

    dispatch({ type: "USER_MESSAGE", text: query })
    ws.send({ message: query, history, model })
  }, [history, model, dispatch, ws, handleSlash])

  useInput((char, key) => {
    if (isThinking && !key.ctrl) return

    if (key.ctrl && char === "c") {
      if (isThinking) {
        ws.close()
        dispatch({ type: "DONE" })
      } else {
        process.exit(0)
      }
      return
    }

    if (key.ctrl && char === "l") { dispatch({ type: "CLEAR" }); return }

    if (key.return) {
      const text = input
      setInput("")
      setCursor(0)
      submit(text)
      return
    }

    if (key.backspace || key.delete) {
      if (cursor > 0) {
        setInput(s => s.slice(0, cursor - 1) + s.slice(cursor))
        setCursor(c => c - 1)
      }
      return
    }

    if (key.leftArrow)  { setCursor(c => Math.max(0, c - 1));             return }
    if (key.rightArrow) { setCursor(c => Math.min(input.length, c + 1));  return }

    if (key.upArrow) {
      const next = Math.min(historyIdx + 1, inputHistory.length - 1)
      setHistoryIdx(next)
      if (inputHistory[next]) { setInput(inputHistory[next]); setCursor(inputHistory[next].length) }
      return
    }

    if (key.downArrow) {
      const next = Math.max(historyIdx - 1, -1)
      setHistoryIdx(next)
      const val = next >= 0 ? inputHistory[next] : ""
      setInput(val); setCursor(val.length)
      return
    }

    if (char && !key.ctrl && !key.meta) {
      setInput(s => s.slice(0, cursor) + char + s.slice(cursor))
      setCursor(c => c + 1)
    }
  })

  return (
    <Box flexDirection="column">
      <Text dimColor> Ask ProteinClaw… (/model /tools /clear /doctor /exit) </Text>
      <Box>
        <Text>{input.slice(0, cursor)}</Text>
        <Text backgroundColor="white" color="black">{input[cursor] ?? " "}</Text>
        <Text>{input.slice(cursor + 1)}</Text>
      </Box>
    </Box>
  )
}
