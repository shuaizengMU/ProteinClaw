export interface CliArgs {
  doctor: boolean
  version: boolean
}

export function parseArgs(argv: string[]): CliArgs {
  const args = argv.slice(2)
  return {
    doctor:  args.includes("--doctor")  || args.includes("-d"),
    version: args.includes("--version") || args.includes("-v"),
  }
}
