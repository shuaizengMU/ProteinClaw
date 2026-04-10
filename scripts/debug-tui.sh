#!/usr/bin/env bash
set -eu

# ────────────────────────────────────────────────────────────────
# ProteinClaw — build and run the TUI in debug mode
#
# Stderr from the TUI (panics, backtraces) → debug.log
# Stderr from the Python server              → server.log
# Both logs are shown after the TUI exits.
#
# Options (env vars):
#   PROTEINCLAW_NO_SPAWN=1   Skip auto-spawning the server.
#                            Run the server yourself first:
#                              uv run proteinclaw server --host 127.0.0.1 --port 8765
#                            Then launch this script with the env var set.
#   PROTEINCLAW_SERVER_CMD=x Override the server binary (e.g. "proteinclaw").
#
# Run from the project root.
# ────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }
info() { echo -e "${BOLD}→${RESET} $*"; }

TUI_LOG="debug.log"
SRV_LOG="server.log"

# ── Prerequisite check ──────────────────────────────────────────
command -v cargo >/dev/null 2>&1 || \
  fail "cargo not found. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
ok "cargo found: $(cargo --version)"

# ── Build (debug profile) ───────────────────────────────────────
info "Building proteinclaw-tui (debug)..."
cargo build -p cli-tui
ok "Build complete → target/debug/proteinclaw-tui"

# ── Pre-flight: start server separately if NO_SPAWN ─────────────
if [ "${PROTEINCLAW_NO_SPAWN:-}" = "1" ]; then
    info "PROTEINCLAW_NO_SPAWN=1 — expecting server already on port 8765"
else
    info "Server stderr → $SRV_LOG"
fi

# ── Run ─────────────────────────────────────────────────────────
BIN="target/debug/proteinclaw-tui"
: > "$TUI_LOG"

info "Launching TUI (debug). TUI stderr → $TUI_LOG  |  Ctrl+C to stop"
echo ""

RUST_BACKTRACE=1 RUST_LOG=debug "$BIN" 2>>"$TUI_LOG" || true

# ── Post-exit: show logs ─────────────────────────────────────────
echo ""
for LOG in "$TUI_LOG" "$SRV_LOG"; do
    if [ -s "$LOG" ]; then
        echo -e "${RED}── $LOG ($(wc -l < "$LOG") lines) ──${RESET}"
        cat "$LOG"
        echo ""
    fi
done

if [ ! -s "$TUI_LOG" ] && [ ! -s "$SRV_LOG" ]; then
    ok "No errors logged. Clean exit."
fi
