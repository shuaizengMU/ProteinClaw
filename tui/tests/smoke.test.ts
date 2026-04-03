import { describe, test, expect } from "bun:test"
import { parseArgs } from "../src/cli"

describe("CLI smoke tests", () => {
  test("parseArgs defaults", () => {
    const args = parseArgs(["bun", "src/main.tsx"])
    expect(args.doctor).toBe(false)
    expect(args.version).toBe(false)
  })

  test("parseArgs --doctor flag", () => {
    const args = parseArgs(["bun", "src/main.tsx", "--doctor"])
    expect(args.doctor).toBe(true)
  })

  test("parseArgs --version flag", () => {
    const args = parseArgs(["bun", "src/main.tsx", "--version"])
    expect(args.version).toBe(true)
  })

  test("parseArgs -d short flag", () => {
    const args = parseArgs(["bun", "src/main.tsx", "-d"])
    expect(args.doctor).toBe(true)
  })
})
