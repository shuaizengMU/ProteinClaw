import { useState, useCallback } from "react"

export function useArrowKeyHistory(history: string[]) {
  const [idx, setIdx] = useState(-1)

  const goUp = useCallback(() => {
    setIdx(i => Math.min(i + 1, history.length - 1))
  }, [history.length])

  const goDown = useCallback(() => {
    setIdx(i => Math.max(i - 1, -1))
  }, [])

  const reset = useCallback(() => setIdx(-1), [])

  const current = idx >= 0 ? history[idx] : null

  return { current, goUp, goDown, reset, idx }
}
