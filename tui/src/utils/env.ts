// Minimal stub for Anthropic-internal env utility
// Only exports what src/ink/terminal.ts and src/ink/termio/osc.ts use

export const env: Record<string, string | undefined> = process.env as Record<string, string | undefined>
