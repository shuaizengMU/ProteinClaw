// Stub for Anthropic-internal bootstrap state
// flushInteractionTime and getSessionId are used for telemetry; noops here.
export function flushInteractionTime(): void {
  // noop
}

export function getSessionId(): string {
  return 'stub-session-id'
}

export function getIsInteractive(): boolean {
  return true
}

export function updateLastInteractionTime(): void {
  // noop
}

export function markScrollActivity(): void {
  // noop stub — ScrollBox scrolling activity tracking not needed in ProteinClaw
}
