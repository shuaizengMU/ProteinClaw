#!/usr/bin/env python3
"""ProteinClaw Tool Harness — data-driven connectivity tests for all tools."""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

# ── Colour helpers ──────────────────────────────────────────────
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SEP = f"{BOLD}{'─' * 50}{RESET}"


def _truncate(text: str, length: int = 80) -> str:
    text = text.replace("\n", " ").strip()
    return text[:length] + "…" if len(text) > length else text


# ── Core runner ─────────────────────────────────────────────────
def run_tool(tool, params: dict) -> tuple[bool, str]:
    """Run a single tool and return (success, message)."""
    result = tool.run(**params)
    if result.success:
        msg = _truncate(result.display) if result.display else "OK"
        return True, msg
    else:
        return False, result.error or "Unknown error"


def main() -> int:
    parser = argparse.ArgumentParser(description="ProteinClaw tool harness")
    parser.add_argument("tools", nargs="*", help="Tool names to test (default: all)")
    parser.add_argument("--skip-slow", action="store_true", help="Skip tools marked as slow (e.g. blast)")
    parser.add_argument("--timeout", type=int, default=30, help="Per-tool timeout in seconds (default: 30)")
    args = parser.parse_args()

    # Load test config
    config_path = Path(__file__).parent / "runnable" / "tool_tests.json"
    with open(config_path) as f:
        test_cases: dict[str, dict] = json.load(f)

    # Discover all registered tools
    from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY
    discover_tools()

    # Filter to requested tools
    if args.tools:
        names = args.tools
    else:
        names = list(test_cases.keys())

    print(f"\n{BOLD}ProteinClaw Tool Harness{RESET}")
    print(SEP)

    passed = 0
    failed = 0
    skipped = 0
    errors: list[tuple[str, str]] = []

    for name in names:
        # Check tool exists in config
        if name not in test_cases:
            print(f"  {YELLOW}?{RESET} {name:<22} not found in tool_tests.json")
            skipped += 1
            continue

        # Check tool is registered
        if name not in TOOL_REGISTRY:
            print(f"  {YELLOW}?{RESET} {name:<22} not in TOOL_REGISTRY (import error?)")
            skipped += 1
            continue

        params = dict(test_cases[name])
        is_slow = params.pop("_slow", False)

        # Skip slow tools if requested
        if is_slow and args.skip_slow:
            print(f"  {DIM}⊘ {name:<22} skipped (slow){RESET}")
            skipped += 1
            continue

        tool = TOOL_REGISTRY[name]
        timeout = args.timeout * 3 if is_slow else args.timeout

        t0 = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_tool, tool, params)
                success, msg = future.result(timeout=timeout)
            elapsed = time.time() - t0

            if success:
                print(f"  {GREEN}✓{RESET} {name:<22} {DIM}({elapsed:.1f}s){RESET}  {_truncate(msg, 60)}")
                passed += 1
            else:
                print(f"  {RED}✗{RESET} {name:<22} {DIM}({elapsed:.1f}s){RESET}  {_truncate(msg, 60)}")
                errors.append((name, msg))
                failed += 1

        except FuturesTimeout:
            elapsed = time.time() - t0
            print(f"  {RED}✗{RESET} {name:<22} {DIM}({elapsed:.1f}s){RESET}  TIMEOUT ({timeout}s)")
            errors.append((name, f"Timeout after {timeout}s"))
            failed += 1
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"  {RED}✗{RESET} {name:<22} {DIM}({elapsed:.1f}s){RESET}  {_truncate(str(exc), 60)}")
            errors.append((name, str(exc)))
            failed += 1

    print(SEP)

    total = passed + failed + skipped
    summary = f"Results: {GREEN}{passed}{RESET} passed"
    if failed:
        summary += f", {RED}{failed}{RESET} failed"
    if skipped:
        summary += f", {DIM}{skipped} skipped{RESET}"
    summary += f" / {total} total"
    print(f"  {summary}")

    if errors:
        print(f"\n{BOLD}Failures:{RESET}")
        for name, msg in errors:
            print(f"  {RED}✗{RESET} {name}: {msg}")

    print()
    return failed


if __name__ == "__main__":
    sys.exit(main())
