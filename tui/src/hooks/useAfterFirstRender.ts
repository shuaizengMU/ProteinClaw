import { useRef, useEffect } from "react"

export function useAfterFirstRender(fn: () => void) {
  const firstRender = useRef(true)
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return }
    fn()
  })
}
