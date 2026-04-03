// Minimal stub for Anthropic-internal execFileNoThrow utility

export async function execFileNoThrow(
  _file: string,
  _args?: string[],
  _options?: Record<string, unknown>,
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  return { stdout: '', stderr: '', exitCode: 1 }
}
