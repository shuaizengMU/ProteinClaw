// Minimal stub for Anthropic-internal envUtils

export function isEnvTruthy(envVar: string | boolean | undefined): boolean {
  if (typeof envVar === 'boolean') return envVar
  if (!envVar) return false
  return ['1', 'true', 'yes'].includes(envVar.toLowerCase())
}

export function isEnvDefinedFalsy(envVar: string | undefined): boolean {
  if (!envVar) return false
  return ['0', 'false', 'no'].includes(envVar.toLowerCase())
}

export function getClaudeConfigHomeDir(): string {
  return process.env.CLAUDE_CONFIG_DIR ?? `${process.env.HOME ?? '~'}/.claude`
}
