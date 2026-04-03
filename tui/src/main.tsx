import React from "react"
import { openSync } from "fs"
import { ReadStream } from "tty"
import { parseArgs } from "./cli.js"
import { loadConfig, needsSetup } from "./services/config.js"
import { createWsClient } from "./services/ws.js"
import { createAppStore } from "./state/AppStateStore.js"
import { setStore, useAppState } from "./state/selectors.js"
import { Setup }  from "./screens/Setup.js"
import { REPL }   from "./screens/REPL.js"
import { Doctor } from "./screens/Doctor.js"
import { renderSync } from "./ink/root.js"

/** Get a usable TTY stdin stream. On Bun/WSL2, process.stdin.isTTY can be
 *  false even in an interactive terminal; opening /dev/tty directly fixes it. */
function getTTYStdin(): NodeJS.ReadStream {
  if (process.stdin.isTTY) return process.stdin
  try {
    const fd = openSync("/dev/tty", "r+")
    return new ReadStream(fd) as NodeJS.ReadStream
  } catch {
    return process.stdin
  }
}

const VERSION = "0.1.0"

async function findFreePort(start = 8000): Promise<number> {
  for (let p = start; p < 65000; p++) {
    try {
      const server = Bun.listen({
        hostname: "127.0.0.1",
        port: p,
        socket: { data() {}, open() {}, close() {}, error() {} },
      })
      server.stop(true)
      return p
    } catch {
      // port in use, try next
    }
  }
  throw new Error("No free port found")
}

async function spawnPythonServer(port: number): Promise<{ kill: () => void }> {
  const python = (await Bun.which("python3")) ?? (await Bun.which("python")) ?? "python3"
  const proc = Bun.spawn(
    [python, "-m", "uvicorn", "proteinclaw.server.main:app", "--host", "127.0.0.1", "--port", String(port)],
    { stdout: "ignore", stderr: "ignore" },
  )
  return { kill: () => proc.kill() }
}

async function waitForServer(port: number, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      await fetch(`http://127.0.0.1:${port}/health`)
      return
    } catch {
      try {
        const conn = await Bun.connect({
          hostname: "127.0.0.1",
          port,
          socket: { data() {}, open() {}, close() {}, error() {} },
        })
        conn.end()
        await Bun.sleep(300)
        return
      } catch {}
    }
    await Bun.sleep(500)
  }
  throw new Error(`Python server did not start within ${timeoutMs}ms`)
}

function App({ ws }: { ws: ReturnType<typeof createWsClient> }) {
  const view = useAppState(s => s.view)

  return (
    <>
      {view === "setup"  && <Setup />}
      {view === "repl"   && <REPL ws={ws} />}
      {view === "doctor" && <Doctor />}
    </>
  )
}

async function main() {
  const args = parseArgs(process.argv)

  if (args.version) {
    console.log(`proteinclaw-tui ${VERSION}`)
    process.exit(0)
  }

  const cfg   = loadConfig()
  const store = createAppStore({ defaultModel: cfg.defaultModel, needsSetup: needsSetup(cfg) })
  setStore(store)

  if (args.doctor) {
    store.dispatch({ type: "SET_VIEW", view: "doctor" })
  }

  process.stderr.write("Starting ProteinClaw server...\n")
  const port   = await findFreePort(8000)
  const server = await spawnPythonServer(port)

  try {
    await waitForServer(port)
  } catch (err) {
    process.stderr.write(`Error: ${err}\n`)
    server.kill()
    process.exit(1)
  }

  process.stderr.write(`Server ready on port ${port}\n`)
  store.dispatch({ type: "SERVER_PORT", port })

  const ws = createWsClient(port)

  process.on("exit",   () => { ws.close(); server.kill() })
  process.on("SIGINT", () => { ws.close(); server.kill(); process.exit(0) })

  renderSync(<App ws={ws} />, { stdin: getTTYStdin() })
}

main().catch(err => {
  process.stderr.write(`Fatal: ${err}\n`)
  process.exit(1)
})
