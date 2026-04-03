import { useState, useEffect } from "react"

export function useElapsedTime(running: boolean): string {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (!running) { setSeconds(0); return }
    const id = setInterval(() => setSeconds(s => s + 1), 1000)
    return () => clearInterval(id)
  }, [running])

  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}m${s}s` : `${s}s`
}
